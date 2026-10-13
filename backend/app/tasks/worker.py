import hashlib
import json
import time
from datetime import timedelta
from celery import Celery
from sqlalchemy import delete, text
from app import create_app
from app.extensions import db
from app.models import (
    Job,
    Project,
    Snapshot,
    SourceFile,
    Chunk,
    Message,
    Conversation,
    Citation,
    Guide,
    Outbox,
    Usage,
    Audit,
    now,
)
from app.services.storage import file_path, remove_snapshot
from app.ingestion.chunks import chunks, digest, SourceLineTooLong, LONG_LINE_REASON
from app.providers.gemini import Gemini, public_failure_message
from app.rag.retrieval import retrieve, budget
from app.rag.citations import validate_answer
from app.rag.prompts import GUIDE

flask_app = create_app()
celery = Celery(
    "codebuddy", broker=flask_app.config["CELERY_BROKER_URL"], backend=flask_app.config["CELERY_RESULT_BACKEND"]
)
celery.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    task_soft_time_limit=1800,
    task_time_limit=1860,
    beat_schedule={
        "dispatch": {"task": "dispatch", "schedule": 10.0},
        "cleanup": {"task": "cleanup", "schedule": 3600.0},
    },
)


class Stopped(Exception):
    pass


def checkpoint(jid, stage, completed=None, total=None):
    db.session.expire_all()
    j = db.session.get(Job, jid)
    if not j:
        raise Stopped()
    p = db.session.scalar(db.select(Project).where(Project.id == j.project_id).with_for_update())
    if not p or p.deleting or j.cancel_requested:
        raise Stopped()
    j.stage = stage
    j.status = "running"
    if completed is not None:
        j.completed = completed
    if total is not None:
        j.total = total
    db.session.commit()
    return j


@celery.task(name="dispatch")
def dispatch():
    with flask_app.app_context():
        # Redis transport can fail; persisted outbox remains eligible for the next tick.
        rows = db.session.scalars(db.select(Outbox).join(Job).where(Job.status == "queued")).all()
        for o in rows:
            if o.dispatched_at and (now() - o.dispatched_at).total_seconds() < 60:
                continue
            try:
                run.delay(o.job_id)
            except Exception:
                continue
            o.dispatched_at = now()
            db.session.commit()


@celery.task(name="cleanup")
def cleanup():
    with flask_app.app_context():
        for s in db.session.scalars(
            db.select(Snapshot).where(Snapshot.status == "preview", Snapshot.created_at < now() - timedelta(hours=24))
        ).all():
            remove_snapshot(s.id)
            db.session.delete(s)
        db.session.execute(delete(Audit).where(Audit.created_at < now() - timedelta(days=30)))
        db.session.execute(delete(Usage).where(Usage.created_at < now() - timedelta(days=30)))
        db.session.commit()


@celery.task(name="run")
def run(jid):
    with flask_app.app_context():
        # A dedicated PostgreSQL advisory-lock connection serializes duplicate task deliveries.
        key = int.from_bytes(hashlib.sha256(jid.encode()).digest()[:8], "big", signed=True)
        with db.engine.connect() as lock:
            if not lock.scalar(text("SELECT pg_try_advisory_lock(:key)"), {"key": key}):
                return
            provider = None
            try:
                j = db.session.get(Job, jid)
                if not j or j.status not in {"queued", "running"}:
                    return
                j.attempt += 1
                db.session.commit()
                started = time.monotonic()
                checkpoint(jid, "validating")
                provider = Gemini()
                if j.kind == "ingestion":
                    ingest(jid, provider)
                else:
                    generate(jid, provider)
                j = db.session.get(Job, jid)
                if j:
                    j.usage = dict(j.usage or {}, latency_seconds=round(time.monotonic() - started, 3))
                    db.session.commit()
            except Stopped:
                db.session.rollback()
                j = db.session.get(Job, jid)
                if j:
                    j.status = "cancelled"
                    j.stage = "cancelled"
                    if j.kind == "ingestion":
                        s = db.session.get(Snapshot, j.snapshot_id)
                        if s and s.status != "ready":
                            s.status = "cancelled"
                    db.session.commit()
            except Exception as exc:
                db.session.rollback()
                j = db.session.get(Job, jid)
                if j:
                    j.status = "failed"
                    j.stage = "failed"
                    j.error_code = type(exc).__name__
                    j.error_message = public_failure_message(exc)
                    if j.kind == "ingestion":
                        s = db.session.get(Snapshot, j.snapshot_id)
                        if s and s.status != "ready":
                            s.status = "failed"
                    db.session.commit()
                flask_app.logger.warning("job_failed job=%s type=%s", jid, type(exc).__name__)
            finally:
                if provider:
                    provider.client.close()
                lock.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": key})
                lock.commit()


def ingest(jid, provider):
    j = checkpoint(jid, "parsing")
    sid = j.snapshot_id
    s = db.session.get(Snapshot, sid)
    if s.status == "ready":
        j.status = "completed"
        db.session.commit()
        return
    model = flask_app.config["GEMINI_EMBEDDING_MODEL"]
    cached_vectors = {}
    if s.embedding_model == model and s.embedding_dimension == 768:
        cached_vectors = {
            row.content_hash: row.embedding
            for row in db.session.execute(
                db.select(Chunk.content_hash, Chunk.embedding).where(
                    Chunk.snapshot_id == sid, Chunk.embedding.is_not(None)
                )
            )
        }
    db.session.execute(delete(Chunk).where(Chunk.snapshot_id == sid))
    s.embedding_model = model
    s.embedding_dimension = 768
    db.session.commit()
    files = db.session.scalars(
        db.select(SourceFile).where(SourceFile.snapshot_id == sid).order_by(SourceFile.relative_path)
    ).all()
    count = 0
    for index, f in enumerate(files):
        checkpoint(jid, "chunking", index, len(files))
        try:
            pieces, status = chunks(file_path(f.storage_key).read_text(), f.language)
        except SourceLineTooLong:
            f.parse_status = "excluded-long-line"
            # Older previews may already contain these files. Keep their source
            # available, but explicitly record that they provide no AI evidence.
            s.report = [row for row in (s.report or []) if row["path"] != f.relative_path] + [
                dict(path=f.relative_path, included=False, reason=LONG_LINE_REASON)
            ]
            db.session.commit()
            continue
        f.parse_status = status
        for ordinal, piece in enumerate(pieces):
            count += 1
            if count > flask_app.config["MAX_CHUNKS_PER_PROJECT"]:
                raise ValueError("Chunk quota exceeded")
            db.session.add(
                Chunk(
                    source_file_id=f.id,
                    snapshot_id=sid,
                    ordinal=ordinal,
                    start_line=piece.start,
                    end_line=piece.end,
                    symbol=piece.symbol,
                    text=piece.text,
                    token_estimate=max(1, len(piece.text) // 4),
                    content_hash=digest(piece.text),
                    embedding=cached_vectors.get(digest(piece.text)),
                )
            )
        db.session.commit()
    all_chunks = db.session.scalars(
        db.select(Chunk).where(Chunk.snapshot_id == sid).order_by(Chunk.source_file_id, Chunk.ordinal)
    ).all()
    if not all_chunks:
        raise ValueError("No indexable source remains")
    if sum(c.token_estimate for c in all_chunks) > flask_app.config["MAX_EMBEDDING_TOKENS_PER_SNAPSHOT"]:
        raise ValueError("Snapshot embedding token budget exceeded")
    pending = [c for c in all_chunks if c.embedding is None]
    reused = len(all_chunks) - len(pending)
    for start in range(0, len(pending), 16):
        checkpoint(jid, "embedding", reused + start, len(all_chunks))
        if start:
            time.sleep(flask_app.config["EMBEDDING_BATCH_DELAY_SECONDS"])
            checkpoint(jid, "embedding", reused + start, len(all_chunks))
        batch = pending[start : start + 16]
        vectors = provider.embed([c.text for c in batch])
        for c, v in zip(batch, vectors):
            c.embedding = v
        db.session.commit()
    checkpoint(jid, "finalizing", len(all_chunks), len(all_chunks))
    db.session.execute(
        text(
            "UPDATE code_chunks SET search_vector = to_tsvector('simple', text || ' ' || coalesce(symbol, '')) WHERE snapshot_id = :sid"
        ),
        {"sid": sid},
    )
    j = db.session.get(Job, jid)
    p = db.session.scalar(db.select(Project).where(Project.id == j.project_id).with_for_update())
    db.session.refresh(j)
    if not p or p.deleting or j.cancel_requested:
        raise Stopped()
    s = db.session.get(Snapshot, sid)
    s.status = "ready"
    s.chunk_count = count
    s.embedding_model = flask_app.config["GEMINI_EMBEDDING_MODEL"]
    s.embedding_dimension = 768
    p.active_snapshot_id = sid
    j.status = "completed"
    j.stage = "ready"
    db.session.commit()


def generate(jid, provider):
    j = checkpoint(jid, "retrieving")
    s = db.session.get(Snapshot, j.snapshot_id)
    if not s or s.status != "ready":
        raise ValueError("Snapshot unavailable")
    history = []
    if j.kind == "guide":
        candidates = db.session.scalars(
            db.select(Chunk)
            .join(SourceFile)
            .where(Chunk.snapshot_id == s.id)
            .order_by(SourceFile.relative_path.ilike("%readme%").desc(), SourceFile.relative_path, Chunk.ordinal)
        ).all()
        evidence = budget(candidates)
        question = GUIDE
    else:
        data = j.request_data
        c = db.session.get(Conversation, data["conversation_id"])
        if not c:
            raise Stopped()
        prior = db.session.scalars(
            db.select(Message)
            .where(Message.conversation_id == c.id, Message.role == "user")
            .order_by(Message.created_at.desc())
            .limit(4)
        ).all()
        history = [m.content.get("text", "")[:1000] for m in reversed(prior)]
        question = data["question"]
        evidence = retrieve(s, "\n".join(history + [question])[-8000:], provider, data.get("file_id"))
        if data.get("start_line"):
            selected = db.session.scalars(
                db.select(Chunk)
                .where(
                    Chunk.snapshot_id == s.id,
                    Chunk.source_file_id == data["file_id"],
                    Chunk.start_line <= data["end_line"],
                    Chunk.end_line >= data["start_line"],
                )
                .order_by(Chunk.ordinal)
            ).all()
            evidence = budget(selected) or evidence
    checkpoint(jid, "generating")
    payload = json.dumps(
        dict(question=question, previous_user_questions=history, untrusted_evidence=list(evidence.values()))
    )
    answer, usage = provider.generate(payload)
    checkpoint(jid, "validating")
    result = validate_answer(answer, evidence)
    if len(result["claims"]) != len(answer.claims):
        answer, usage = provider.generate(
            payload + "\nReturn only claims supported by the supplied source IDs; abstain when unsupported."
        )
        result = validate_answer(answer, evidence)
    # An independent support pass can only remove claims; it is a heuristic, not proof of correctness.
    if result["claims"]:
        review, _ = provider.generate(
            json.dumps(
                dict(
                    question="Check each candidate claim against the evidence. Return only supported claims, mark inference, and list missing evidence. Do not add claims.",
                    candidate=result,
                    untrusted_evidence=list(evidence.values()),
                )
            )
        )
        reviewed = validate_answer(review, evidence)
        original = {c["text"] for c in result["claims"]}
        reviewed["claims"] = [c for c in reviewed["claims"] if c["text"] in original]
        if len(reviewed["claims"]) < len(result["claims"]):
            reviewed["answer_status"] = "partial" if reviewed["claims"] else "insufficient_evidence"
        result = reviewed
    checkpoint(jid, "validating")
    j = db.session.get(Job, jid)
    p = db.session.scalar(db.select(Project).where(Project.id == j.project_id).with_for_update())
    db.session.refresh(j)
    if not p or p.deleting or j.cancel_requested:
        raise Stopped()
    if j.kind == "guide":
        db.session.add(Guide(project_id=j.project_id, snapshot_id=j.snapshot_id, content=result, version=j.attempt))
    else:
        if not db.session.get(Conversation, j.request_data["conversation_id"]):
            raise Stopped()
        m = Message(
            conversation_id=j.request_data["conversation_id"],
            role="assistant",
            content=result,
            generation_job_id=j.id,
            regenerated_from=j.request_data.get("regenerated_from"),
        )
        db.session.add(m)
        db.session.flush()
        for c in result["citations"]:
            db.session.add(
                Citation(
                    message_id=m.id,
                    chunk_id=c["source_id"],
                    source_file_id=c["file_id"],
                    snapshot_id=c["snapshot_id"],
                    start_line=c["start_line"],
                    end_line=c["end_line"],
                )
            )
    j.status = "completed"
    j.stage = "completed"
    j.usage = dict(
        provider="gemini",
        model=flask_app.config["GEMINI_GENERATION_MODEL"],
        prompt_version="1",
        retrieval_version="rrf-1",
        tokens=usage,
    )
    db.session.add(Usage(owner_id=j.owner_id, job_id=j.id, details=j.usage))
    db.session.commit()
