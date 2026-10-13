from flask import abort, current_app
from flask_login import current_user
from app.extensions import db
from app.models import Project, Snapshot


def project(pid, lock=False):
    q = db.select(Project).where(Project.id == pid, Project.owner_id == current_user.id, Project.deleting.is_(False))
    p = db.session.scalar(q.with_for_update() if lock else q)
    if not p:
        abort(404)
    return p


def owned(model, ident):
    item = db.session.get(model, ident)
    if not item:
        abort(404)
    if hasattr(item, "owner_id") and item.owner_id != current_user.id:
        abort(404)
    if hasattr(item, "project_id"):
        project(item.project_id)
    return item


def snapshot(p, sid=None, ready=False):
    s = db.session.scalar(
        db.select(Snapshot).where(Snapshot.id == (sid or p.active_snapshot_id), Snapshot.project_id == p.id)
    )
    if not s:
        abort(404)
    if ready and s.status != "ready":
        abort(409, "Snapshot is not ready. Finish indexing first.")
    return s


def require_provider():
    if not current_app.config["GEMINI_API_KEY"]:
        abort(503, "Live AI is unavailable. Configure GEMINI_API_KEY on the server.")
