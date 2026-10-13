"""Initial schema; frozen metadata for reproducible fresh installations."""

from alembic import op
from flask_sqlalchemy import SQLAlchemy

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None
import uuid
from datetime import datetime, timezone
from flask_login import UserMixin
from sqlalchemy.dialects.postgresql import TSVECTOR
from pgvector.sqlalchemy import Vector

db = SQLAlchemy()


def uid():
    return str(uuid.uuid4())


def now():
    return datetime.now(timezone.utc)


class Base(db.Model):
    __abstract__ = True
    id = db.Column(db.String(36), primary_key=True, default=uid)
    created_at = db.Column(db.DateTime(timezone=True), default=now, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=now, onupdate=now, nullable=False)


class User(UserMixin, Base):
    __tablename__ = "users"
    email = db.Column(db.String(254), unique=True, nullable=False)
    display_name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.Text, nullable=False)
    session_version = db.Column(db.Integer, default=1, nullable=False)


class Project(Base):
    __tablename__ = "projects"
    owner_id = db.Column(db.ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, default="")
    active_snapshot_id = db.Column(
        db.ForeignKey("repository_snapshots.id", name="fk_active_snapshot", use_alter=True, ondelete="SET NULL")
    )
    deleting = db.Column(db.Boolean, default=False, nullable=False)


class Snapshot(Base):
    __tablename__ = "repository_snapshots"
    project_id = db.Column(db.ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False)
    label = db.Column(db.String(160), default="Upload")
    source_type = db.Column(db.String(20), default="zip")
    archive_hash = db.Column(db.String(64))
    manifest_hash = db.Column(db.String(64))
    status = db.Column(db.String(24), default="preview", nullable=False)
    file_count = db.Column(db.Integer, default=0)
    chunk_count = db.Column(db.Integer, default=0)
    embedding_model = db.Column(db.String(100))
    embedding_dimension = db.Column(db.Integer, default=768)
    pipeline_version = db.Column(db.String(30), default="1")
    report = db.Column(db.JSON, default=list)


class SourceFile(Base):
    __tablename__ = "source_files"
    snapshot_id = db.Column(db.ForeignKey("repository_snapshots.id", ondelete="CASCADE"), index=True, nullable=False)
    relative_path = db.Column(db.Text, nullable=False)
    language = db.Column(db.String(30), nullable=False)
    storage_key = db.Column(db.String(100), nullable=False)
    content_hash = db.Column(db.String(64), nullable=False)
    line_count = db.Column(db.Integer, nullable=False)
    size = db.Column(db.Integer, nullable=False)
    parse_status = db.Column(db.String(30), default="pending")
    __table_args__ = (db.UniqueConstraint("snapshot_id", "relative_path"),)


class Chunk(Base):
    __tablename__ = "code_chunks"
    source_file_id = db.Column(db.ForeignKey("source_files.id", ondelete="CASCADE"), index=True, nullable=False)
    snapshot_id = db.Column(db.ForeignKey("repository_snapshots.id", ondelete="CASCADE"), index=True, nullable=False)
    ordinal = db.Column(db.Integer, nullable=False)
    start_line = db.Column(db.Integer, nullable=False)
    end_line = db.Column(db.Integer, nullable=False)
    symbol = db.Column(db.String(250))
    text = db.Column(db.Text, nullable=False)
    token_estimate = db.Column(db.Integer, nullable=False)
    content_hash = db.Column(db.String(64), nullable=False)
    search_vector = db.Column(TSVECTOR().with_variant(db.Text, "sqlite"))
    embedding = db.Column(Vector(768).with_variant(db.JSON, "sqlite"))
    __table_args__ = (
        db.UniqueConstraint("source_file_id", "ordinal"),
        db.CheckConstraint("start_line >= 1 AND end_line >= start_line"),
    )


class Conversation(Base):
    __tablename__ = "conversations"
    owner_id = db.Column(db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    project_id = db.Column(db.ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False)
    snapshot_id = db.Column(db.ForeignKey("repository_snapshots.id", ondelete="CASCADE"), nullable=False)
    title = db.Column(db.String(160), default="New conversation")


class Job(Base):
    __tablename__ = "generation_jobs"
    owner_id = db.Column(db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    project_id = db.Column(db.ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False)
    snapshot_id = db.Column(db.ForeignKey("repository_snapshots.id", ondelete="CASCADE"), nullable=False)
    kind = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(30), default="queued", nullable=False)
    stage = db.Column(db.String(30), default="queued")
    completed = db.Column(db.Integer, default=0)
    total = db.Column(db.Integer, default=0)
    attempt = db.Column(db.Integer, default=0)
    cancel_requested = db.Column(db.Boolean, default=False)
    idempotency_key = db.Column(db.String(128), nullable=False)
    request_data = db.Column(db.JSON, default=dict)
    usage = db.Column(db.JSON, default=dict)
    error_code = db.Column(db.String(60))
    error_message = db.Column(db.String(300))
    __table_args__ = (db.UniqueConstraint("owner_id", "idempotency_key"),)


class Message(Base):
    __tablename__ = "messages"
    conversation_id = db.Column(db.ForeignKey("conversations.id", ondelete="CASCADE"), index=True, nullable=False)
    role = db.Column(db.String(20), nullable=False)
    content = db.Column(db.JSON, nullable=False)
    status = db.Column(db.String(30), default="completed")
    generation_job_id = db.Column(db.ForeignKey("generation_jobs.id", ondelete="SET NULL"))
    regenerated_from = db.Column(db.ForeignKey("messages.id", ondelete="SET NULL"))


class Citation(Base):
    __tablename__ = "citations"
    message_id = db.Column(db.ForeignKey("messages.id", ondelete="CASCADE"), nullable=False)
    chunk_id = db.Column(db.ForeignKey("code_chunks.id", ondelete="CASCADE"), nullable=False)
    source_file_id = db.Column(db.ForeignKey("source_files.id", ondelete="CASCADE"), nullable=False)
    snapshot_id = db.Column(db.ForeignKey("repository_snapshots.id", ondelete="CASCADE"), nullable=False)
    start_line = db.Column(db.Integer, nullable=False)
    end_line = db.Column(db.Integer, nullable=False)


class Guide(Base):
    __tablename__ = "onboarding_guides"
    project_id = db.Column(db.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    snapshot_id = db.Column(db.ForeignKey("repository_snapshots.id", ondelete="CASCADE"), nullable=False)
    content = db.Column(db.JSON, nullable=False)
    status = db.Column(db.String(30), default="completed")
    version = db.Column(db.Integer, default=1)


class Feedback(Base):
    __tablename__ = "answer_feedback"
    message_id = db.Column(db.ForeignKey("messages.id", ondelete="CASCADE"), nullable=False)
    user_id = db.Column(db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.String(1000), default="")
    __table_args__ = (db.UniqueConstraint("message_id", "user_id"), db.CheckConstraint("rating IN (-1, 1)"))


class Outbox(Base):
    __tablename__ = "outbox_events"
    job_id = db.Column(db.ForeignKey("generation_jobs.id", ondelete="CASCADE"), unique=True, nullable=False)
    dispatched_at = db.Column(db.DateTime(timezone=True))


class Audit(Base):
    __tablename__ = "audit_events"
    owner_id = db.Column(db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    action = db.Column(db.String(50), nullable=False)
    details = db.Column(db.JSON, default=dict)


class Usage(Base):
    __tablename__ = "usage_events"
    owner_id = db.Column(db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    job_id = db.Column(db.ForeignKey("generation_jobs.id", ondelete="CASCADE"), nullable=False)
    details = db.Column(db.JSON, default=dict)


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    db.metadata.create_all(op.get_bind())
    op.execute("CREATE INDEX ix_chunks_fts ON code_chunks USING gin(search_vector)")


def downgrade():
    db.metadata.drop_all(op.get_bind())
