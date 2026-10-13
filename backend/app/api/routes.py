import hashlib
import json
import secrets
import time
from datetime import timedelta
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError
from flask import Blueprint, abort, current_app, jsonify, request, session, Response, stream_with_context
from flask_login import current_user, login_required, login_user, logout_user
from flask_wtf.csrf import generate_csrf
from sqlalchemy import func, text
from sqlalchemy.exc import IntegrityError
from app.extensions import db, limiter
from app.models import (
    User,
    Project,
    Snapshot,
    SourceFile,
    Job,
    Conversation,
    Message,
    Guide,
    Feedback,
    Outbox,
    now,
    uid,
)
from app.schemas import Register, Login, ProjectInput, Question
from app.services.access import project, owned, snapshot, require_provider
from app.services.storage import write_source, file_path, remove_snapshot
from app.ingestion.archive import inspect_zip, UnsafeArchive

api = Blueprint("api", __name__)
passwords = PasswordHasher()
DUMMY_HASH = passwords.hash("dummy-password-for-timing-only")


def body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        abort(400, "Expected a JSON object")
    return data


def serial(item):
    result = {}
    for col in item.__table__.columns:
        if col.name in {
            "password_hash",
            "storage_key",
            "embedding",
            "search_vector",
            "request_data",
            "session_version",
        }:
            continue
        v = getattr(item, col.name)
        result[col.name] = v.isoformat() if hasattr(v, "isoformat") else v
    if isinstance(item, Project):
        active = db.session.get(Snapshot, item.active_snapshot_id) if item.active_snapshot_id else None
        result["file_count"] = active.file_count if active else 0
        result["last_indexed_at"] = active.updated_at.isoformat() if active else None
        result["languages"] = (
            list(
                db.session.scalars(db.select(SourceFile.language).where(SourceFile.snapshot_id == active.id).distinct())
            )
            if active
            else []
        )
    return result


def page(query):
    try:
        offset = max(0, int(request.args.get("offset", 0)))
        limit = min(100, max(1, int(request.args.get("limit", 50))))
    except ValueError:
        abort(400, "Invalid pagination")
    return jsonify(
        items=[serial(x) for x in db.session.scalars(query.offset(offset).limit(limit))], offset=offset, limit=limit
    )


def authenticate(user):
    session.clear()
    session["rotation"] = secrets.token_urlsafe(24)
    current_app.session_interface.regenerate(session)
    session["version"] = user.session_version
    login_user(user, remember=False)
    return jsonify(user=serial(user), csrf_token=generate_csrf())


@api.get("/auth/csrf")
def csrf_token():
    return jsonify(csrf_token=generate_csrf())


@api.post("/auth/register")
@limiter.limit("5 per hour")
def register():
    data = Register.model_validate(body())
    user = User(
        email=str(data.email).lower(), display_name=data.display_name, password_hash=passwords.hash(data.password)
    )
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        abort(409, "Unable to register this email. Try signing in.")
    return authenticate(user), 201


@api.post("/auth/login")
@limiter.limit("10 per minute")
def login():
    data = Login.model_validate(body())
    user = db.session.scalar(db.select(User).where(User.email == str(data.email).lower()))
    try:
        valid = passwords.verify(user.password_hash if user else DUMMY_HASH, data.password)
    except (VerifyMismatchError, InvalidHashError):
        valid = False
    if not user or not valid:
        abort(401, "Email or password is incorrect")
    return authenticate(user)


@api.post("/auth/logout")
@login_required
def logout():
    logout_user()
    session.clear()
    return jsonify(ok=True)


@api.get("/auth/me")
@login_required
def me():
    return jsonify(user=serial(current_user), ai_available=bool(current_app.config["GEMINI_API_KEY"]))


@api.route("/account", methods=["PATCH", "DELETE"])
@login_required
def account():
    data = body()
    password = data.get("password", "")
    if not isinstance(password, str) or not 1 <= len(password) <= 128:
        abort(422, "Enter a valid current password")
    try:
        passwords.verify(current_user.password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        abort(403, "Enter your current password")
    if request.method == "DELETE":
        for p in db.session.scalars(db.select(Project).where(Project.owner_id == current_user.id)).all():
            delete_project(p)
        db.session.delete(db.session.get(User, current_user.id))
        db.session.commit()
        logout_user()
        session.clear()
        return jsonify(ok=True)
    name = str(data.get("display_name", "")).strip()
    if not 1 <= len(name) <= 100:
        abort(422, "Display name must be 1–100 characters")
    current_user.display_name = name
    db.session.commit()
    return jsonify(user=serial(current_user))


@api.route("/projects", methods=["GET", "POST"])
@login_required
def projects():
    if request.method == "GET":
        return page(
            db.select(Project)
            .where(Project.owner_id == current_user.id, Project.deleting.is_(False))
            .order_by(Project.created_at.desc())
        )
    data = ProjectInput.model_validate(body())
    if db.session.scalar(db.select(func.count()).select_from(Project).where(Project.owner_id == current_user.id)) >= 20:
        abort(409, "Project quota reached (20)")
    p = Project(owner_id=current_user.id, **data.model_dump())
    db.session.add(p)
    db.session.commit()
    return jsonify(serial(p)), 201


def delete_project(p):
    p = db.session.scalar(db.select(Project).where(Project.id == p.id).with_for_update())
    p.deleting = True
    for job in db.session.scalars(db.select(Job).where(Job.project_id == p.id)):
        job.cancel_requested = True
    ids = list(db.session.scalars(db.select(Snapshot.id).where(Snapshot.project_id == p.id)))
    db.session.commit()
    for sid in ids:
        remove_snapshot(sid)
    db.session.delete(p)
    db.session.commit()


@api.route("/projects/<pid>", methods=["GET", "PATCH", "DELETE"])
@login_required
def project_detail(pid):
    p = project(pid)
    if request.method == "DELETE":
        delete_project(p)
        return jsonify(ok=True)
    if request.method == "PATCH":
        data = ProjectInput.model_validate(body())
        p.name = data.name
        p.description = data.description
        db.session.commit()
    result = serial(p)
    result["jobs"] = [
        serial(j)
        for j in db.session.scalars(
            db.select(Job)
            .where(Job.project_id == p.id, Job.status.in_(["queued", "running", "failed", "cancelled"]))
            .order_by(Job.created_at.desc())
            .limit(20)
        )
    ]
    result["snapshots"] = [
        serial(s)
        for s in db.session.scalars(
            db.select(Snapshot).where(Snapshot.project_id == p.id).order_by(Snapshot.created_at.desc())
        )
    ]
    return jsonify(result)


@api.post("/projects/<pid>/uploads")
@login_required
@limiter.limit("10 per hour")
def upload(pid):
    db.session.scalar(db.select(User).where(User.id == current_user.id).with_for_update())
    p = project(pid, lock=True)
    upload = request.files.get("file")
    if not upload:
        abort(400, "Select a ZIP file")
    total = db.session.scalar(
        db.select(func.coalesce(func.sum(SourceFile.size), 0))
        .join(Snapshot, SourceFile.snapshot_id == Snapshot.id)
        .join(Project, Snapshot.project_id == Project.id)
        .where(Project.owner_id == current_user.id)
    )
    if total >= 500 * 1024**2:
        abort(409, "Account storage quota reached (500 MiB). Delete old projects.")
    data = upload.read(current_app.config["MAX_UPLOAD_MB"] * 1024**2 + 1)
    exclusions = request.form.get("exclusions", "").splitlines()[:200]
    try:
        files, report = inspect_zip(data, current_app.config, exclusions)
    except (UnsafeArchive, ValueError) as exc:
        abort(422, str(exc))
    if total + sum(len(f["text"].encode()) for f in files) > 500 * 1024**2:
        abort(409, "Account storage quota exceeded")
    s = Snapshot(
        id=uid(),
        project_id=p.id,
        label="Source upload",
        archive_hash=hashlib.sha256(data).hexdigest(),
        report=report,
        file_count=len(files),
    )
    s.manifest_hash = hashlib.sha256(
        "".join(f["path"] + f["hash"] for f in sorted(files, key=lambda f: f["path"])).encode()
    ).hexdigest()
    db.session.add(s)
    try:
        for f in files:
            ident = uid()
            key = write_source(s.id, ident, f["text"])
            db.session.add(
                SourceFile(
                    id=ident,
                    snapshot_id=s.id,
                    relative_path=f["path"],
                    language=f["language"],
                    storage_key=key,
                    content_hash=f["hash"],
                    line_count=len(f["text"].splitlines()),
                    size=len(f["text"].encode()),
                )
            )
        db.session.commit()
    except Exception:
        db.session.rollback()
        remove_snapshot(s.id)
        raise
    return jsonify(serial(s)), 201


@api.route("/uploads/<sid>", methods=["GET", "DELETE"])
@login_required
def upload_detail(sid):
    s = owned(Snapshot, sid)
    if request.method == "DELETE":
        if s.status not in {"preview", "failed", "cancelled"}:
            abort(409, "Cancel processing before discarding")
        remove_snapshot(s.id)
        db.session.delete(s)
        db.session.commit()
        return jsonify(ok=True)
    return jsonify(serial(s))


def queue_job(p, s, kind, data):
    key = request.headers.get("Idempotency-Key", "")
    if not 8 <= len(key) <= 128:
        abort(400, "Provide an Idempotency-Key header (8–128 characters)")
    old = db.session.scalar(db.select(Job).where(Job.owner_id == current_user.id, Job.idempotency_key == key))
    if old:
        if old.project_id != p.id or old.snapshot_id != s.id or old.kind != kind or old.request_data != data:
            abort(409, "Idempotency key was used for another request")
        return old, False
    used = db.session.scalar(
        db.select(func.count())
        .select_from(Job)
        .where(Job.owner_id == current_user.id, Job.created_at >= now() - timedelta(days=1))
    )
    if used >= 100:
        abort(429, "Daily AI job limit reached (100). Try tomorrow.")
    job = Job(
        id=uid(),
        owner_id=current_user.id,
        project_id=p.id,
        snapshot_id=s.id,
        kind=kind,
        idempotency_key=key,
        request_data=data,
    )
    db.session.add(job)
    db.session.add(Outbox(job_id=job.id))
    return job, True


@api.post("/uploads/<sid>/index")
@login_required
def index(sid):
    s = owned(Snapshot, sid)
    p = project(s.project_id, lock=True)
    require_provider()
    if s.status not in {"preview", "queued"}:
        abort(409, "This snapshot cannot be indexed again. Re-upload for a new snapshot.")
    data = body()
    if data.get("consent") is not True:
        abort(422, "Confirm that sanitized source can be sent to Gemini")
    removed_keys = []
    excluded = data.get("exclude_file_ids", [])
    if not isinstance(excluded, list) or len(excluded) > 2000:
        abort(422)
    if s.status == "preview":
        for ident in excluded:
            f = db.session.scalar(db.select(SourceFile).where(SourceFile.id == ident, SourceFile.snapshot_id == sid))
            if not f:
                abort(404)
            removed_keys.append(f.storage_key)
            db.session.delete(f)
        db.session.flush()
        s.file_count = db.session.scalar(
            db.select(func.count()).select_from(SourceFile).where(SourceFile.snapshot_id == sid)
        )
        if not s.file_count:
            abort(422, "Keep at least one source file")
    job, _ = queue_job(p, s, "ingestion", {})
    s.status = "queued"
    db.session.commit()
    for key in removed_keys:
        file_path(key).unlink(missing_ok=True)
    return jsonify(serial(job)), 202


@api.get("/projects/<pid>/snapshots")
@login_required
def snapshots(pid):
    p = project(pid)
    return page(db.select(Snapshot).where(Snapshot.project_id == p.id).order_by(Snapshot.created_at.desc()))


@api.get("/projects/<pid>/files")
@login_required
def files(pid):
    s = snapshot(project(pid), request.args.get("snapshot_id"))
    return page(db.select(SourceFile).where(SourceFile.snapshot_id == s.id).order_by(SourceFile.relative_path))


@api.get("/projects/<pid>/files/<fid>")
@login_required
def source(pid, fid):
    s = snapshot(project(pid), request.args.get("snapshot_id"))
    f = db.session.scalar(db.select(SourceFile).where(SourceFile.id == fid, SourceFile.snapshot_id == s.id))
    if not f:
        abort(404)
    try:
        start = int(request.args.get("start_line", 1))
        end = int(request.args.get("end_line", f.line_count))
    except ValueError:
        abort(422)
    if not 1 <= start <= end <= f.line_count:
        abort(422, "Invalid inclusive line range")
    return jsonify(
        **serial(f),
        start_line=start,
        end_line=end,
        text="\n".join(file_path(f.storage_key).read_text().splitlines()[start - 1 : end]),
    )


@api.get("/projects/<pid>/search")
@login_required
@limiter.limit("30 per minute")
def search(pid):
    s = snapshot(project(pid), request.args.get("snapshot_id"), ready=True)
    require_provider()
    question = request.args.get("q", "").strip()
    if not 1 <= len(question) <= current_app.config["MAX_QUESTION_CHARS"]:
        abort(422)
    from app.providers.gemini import Gemini
    from app.rag.retrieval import retrieve

    return jsonify(items=list(retrieve(s, question, Gemini()).values()))


@api.route("/projects/<pid>/conversations", methods=["GET", "POST"])
@login_required
def conversations(pid):
    p = project(pid)
    if request.method == "GET":
        return page(
            db.select(Conversation).where(Conversation.project_id == p.id).order_by(Conversation.created_at.desc())
        )
    s = snapshot(p, body().get("snapshot_id"), ready=True)
    c = Conversation(owner_id=current_user.id, project_id=p.id, snapshot_id=s.id)
    db.session.add(c)
    db.session.commit()
    return jsonify(serial(c)), 201


@api.route("/conversations/<cid>", methods=["GET", "DELETE"])
@login_required
def conversation(cid):
    c = owned(Conversation, cid)
    if request.method == "DELETE":
        for job in db.session.scalars(db.select(Job).where(Job.project_id == c.project_id)):
            if job.request_data.get("conversation_id") == c.id:
                job.cancel_requested = True
        db.session.delete(c)
        db.session.commit()
        return jsonify(ok=True)
    result = serial(c)
    result["jobs"] = [
        serial(j)
        for j in db.session.scalars(
            db.select(Job).where(Job.project_id == c.project_id).order_by(Job.created_at.desc()).limit(100)
        )
        if j.request_data.get("conversation_id") == c.id
    ]
    return jsonify(result)


@api.route("/conversations/<cid>/messages", methods=["GET", "POST"])
@login_required
@limiter.limit("30 per minute")
def messages(cid):
    c = owned(Conversation, cid)
    if request.method == "GET":
        return page(db.select(Message).where(Message.conversation_id == c.id).order_by(Message.created_at))
    require_provider()
    q = Question.model_validate(body())
    p = project(c.project_id, lock=True)
    s = snapshot(p, c.snapshot_id, ready=True)
    if len(q.question) > current_app.config["MAX_QUESTION_CHARS"]:
        abort(422)
    if q.file_id:
        f = db.session.scalar(db.select(SourceFile).where(SourceFile.id == q.file_id, SourceFile.snapshot_id == s.id))
        if not f:
            abort(404)
        if q.start_line and not (q.end_line and 1 <= q.start_line <= q.end_line <= f.line_count):
            abort(422)
    elif q.start_line or q.end_line:
        abort(422)
    data = dict(conversation_id=c.id, **q.model_dump())
    job, fresh = queue_job(p, s, "answer", data)
    if fresh:
        db.session.add(
            Message(conversation_id=c.id, role="user", content={"text": q.question}, generation_job_id=job.id)
        )
        c.title = q.question[:160]
    db.session.commit()
    return jsonify(serial(job)), 202


@api.post("/messages/<mid>/regenerate")
@login_required
def regenerate(mid):
    m = db.session.get(Message, mid)
    if not m:
        abort(404)
    c = owned(Conversation, m.conversation_id)
    require_provider()
    old = owned(Job, m.generation_job_id)
    data = dict(old.request_data, regenerated_from=m.id)
    j, _ = queue_job(
        project(c.project_id, lock=True), snapshot(project(c.project_id), c.snapshot_id, True), "answer", data
    )
    db.session.commit()
    return jsonify(serial(j)), 202


@api.post("/messages/<mid>/feedback")
@login_required
def feedback(mid):
    m = db.session.get(Message, mid)
    if not m:
        abort(404)
    owned(Conversation, m.conversation_id)
    data = body()
    if m.role != "assistant" or data.get("rating") not in [-1, 1] or len(str(data.get("comment", ""))) > 1000:
        abort(422)
    f = db.session.scalar(db.select(Feedback).where(Feedback.message_id == mid, Feedback.user_id == current_user.id))
    if not f:
        f = Feedback(message_id=mid, user_id=current_user.id)
        db.session.add(f)
    f.rating = data["rating"]
    f.comment = str(data.get("comment", ""))
    db.session.commit()
    return jsonify(ok=True)


@api.route("/projects/<pid>/guides", methods=["GET", "POST"])
@login_required
def guides(pid):
    p = project(pid)
    s = snapshot(p, request.args.get("snapshot_id"), ready=True)
    if request.method == "GET":
        return page(
            db.select(Guide)
            .where(Guide.project_id == p.id, Guide.snapshot_id == s.id)
            .order_by(Guide.created_at.desc())
        )
    require_provider()
    j, _ = queue_job(project(pid, lock=True), s, "guide", {})
    db.session.commit()
    return jsonify(serial(j)), 202


@api.get("/guides/<gid>/export")
@login_required
def export(gid):
    guide = owned(Guide, gid)
    lines = ["# CodeBuddy onboarding guide", f"Snapshot: {guide.snapshot_id}", ""]
    cites = {c["source_id"]: c for c in guide.content.get("citations", [])}
    for c in guide.content["claims"]:
        lines.append(f"{c['evidence_kind'].title()}: {c['text']}")
        for ident in c["source_ids"]:
            e = cites[ident]
            lines.append(f"Source: `{e['path']}` lines {e['start_line']}–{e['end_line']}")
        lines.append("")
    lines += ["## Limitations", *guide.content["limitations"]]
    return Response(
        "\n".join(lines),
        mimetype="text/markdown",
        headers={"Content-Disposition": 'attachment; filename="codebuddy-guide.md"'},
    )


@api.get("/jobs/<jid>")
@login_required
def job(jid):
    return jsonify(serial(owned(Job, jid)))


@api.post("/jobs/<jid>/cancel")
@login_required
def cancel(jid):
    j = owned(Job, jid)
    if j.status not in {"completed", "failed", "cancelled"}:
        j.cancel_requested = True
    db.session.commit()
    return jsonify(serial(j))


@api.post("/jobs/<jid>/retry")
@login_required
def retry(jid):
    require_provider()
    j = owned(Job, jid)
    project(j.project_id, lock=True)
    if j.status not in {"failed", "cancelled"} or j.attempt >= 3:
        abort(409, "Only failed/cancelled jobs below three attempts can retry")
    j.status = "queued"
    j.stage = "queued"
    j.cancel_requested = False
    j.error_code = None
    j.error_message = None
    if j.kind == "ingestion":
        s = db.session.get(Snapshot, j.snapshot_id)
        if not s:
            abort(409, "The source snapshot is unavailable. Upload it again.")
        if s.status != "ready":
            s.status = "queued"
    o = db.session.scalar(db.select(Outbox).where(Outbox.job_id == j.id))
    o.dispatched_at = None
    db.session.commit()
    return jsonify(serial(j)), 202


@api.get("/jobs/<jid>/events")
@login_required
@limiter.limit("12 per minute")
def events(jid):
    owned(Job, jid)
    owner = current_user.id

    @stream_with_context
    def stream():
        previous = request.headers.get("Last-Event-ID", "")
        for _ in range(30):
            db.session.expire_all()
            current = db.session.get(Job, jid)
            if not current or current.owner_id != owner:
                break
            p = db.session.get(Project, current.project_id)
            if not p or p.deleting:
                break
            version = current.updated_at.isoformat()
            payload = serial(current)
            db.session.remove()
            if version != previous:
                yield f"id: {version}\nevent: status\ndata: {json.dumps(payload)}\n\n"
                previous = version
            else:
                yield ": heartbeat\n\n"
            if payload["status"] in {"completed", "failed", "cancelled"}:
                break
            time.sleep(2)

    return Response(stream(), mimetype="text/event-stream", headers={"X-Accel-Buffering": "no"})


@api.get("/health/live")
@limiter.exempt
def live():
    return jsonify(status="ok")


@api.get("/health/ready")
@limiter.exempt
def ready():
    try:
        db.session.execute(text("SELECT 1"))
        current_app.config["SESSION_REDIS"].ping()
        return jsonify(status="ready")
    except Exception:
        return jsonify(status="unavailable"), 503
