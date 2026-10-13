from sqlalchemy import func, or_
from flask import current_app
from app.extensions import db
from app.models import Chunk, SourceFile


def rrf(*rankings):
    scores = {}
    for ranking in rankings:
        for rank, ident in enumerate(ranking, 1):
            scores[ident] = scores.get(ident, 0) + 1 / (60 + rank)
    return sorted(scores, key=lambda i: (-scores[i], i))


def retrieve(snapshot, question, provider, file_id=None):
    if snapshot.embedding_model != current_app.config["GEMINI_EMBEDDING_MODEL"] or snapshot.embedding_dimension != 768:
        raise ValueError("Embedding configuration changed. Reindex before querying this snapshot.")
    vector = provider.embed([question], query=True)[0]
    q = db.select(Chunk).where(Chunk.snapshot_id == snapshot.id)
    if file_id:
        q = q.where(Chunk.source_file_id == file_id)
    semantic = db.session.scalars(q.order_by(Chunk.embedding.cosine_distance(vector)).limit(20)).all()
    terms = func.plainto_tsquery("simple", question)
    lexical = db.session.scalars(
        q.where(Chunk.search_vector.op("@@")(terms))
        .order_by(func.ts_rank_cd(Chunk.search_vector, terms).desc())
        .limit(20)
    ).all()
    # An exact identifier/path branch complements PostgreSQL tokenization.
    identifiers = [t.strip("?.,`'\"") for t in question.split() if len(t) > 2][:20]
    exact = []
    if identifiers:
        exact = db.session.scalars(
            q.join(SourceFile, SourceFile.id == Chunk.source_file_id)
            .where(or_(Chunk.symbol.in_(identifiers), SourceFile.relative_path.in_(identifiers)))
            .limit(20)
        ).all()
    all_chunks = {c.id: c for c in semantic + lexical + exact}
    ranked = rrf([c.id for c in semantic], [c.id for c in lexical], [c.id for c in exact])
    return budget([all_chunks[i] for i in ranked])


def budget(chunks):
    evidence = {}
    tokens = 0
    covered = []
    for c in chunks:
        if any(fid == c.source_file_id and a <= c.start_line and b >= c.end_line for fid, a, b in covered):
            continue
        if tokens + c.token_estimate > current_app.config["MAX_CONTEXT_TOKENS"]:
            continue
        f = db.session.get(SourceFile, c.source_file_id)
        if not f or f.snapshot_id != c.snapshot_id or not 1 <= c.start_line <= c.end_line <= f.line_count:
            raise ValueError("Inconsistent source evidence")
        evidence[c.id] = dict(
            source_id=c.id,
            file_id=f.id,
            snapshot_id=c.snapshot_id,
            path=f.relative_path,
            start_line=c.start_line,
            end_line=c.end_line,
            line_count=f.line_count,
            text=c.text,
        )
        tokens += c.token_estimate
        covered.append((f.id, c.start_line, c.end_line))
        if len(evidence) >= 10:
            break
    return evidence
