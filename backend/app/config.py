import os
from datetime import timedelta


def settings():
    e = os.environ
    cfg = dict(
        SECRET_KEY=e.get("APP_SECRET_KEY") or "development-only-change-before-production",
        SQLALCHEMY_DATABASE_URI=e.get(
            "DATABASE_URL", "postgresql+psycopg://codebuddy:codebuddy@localhost:5432/codebuddy"
        ),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SESSION_TYPE="redis",
        SESSION_PERMANENT=True,
        SESSION_USE_SIGNER=True,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=e.get("APP_ENV") == "production",
        PERMANENT_SESSION_LIFETIME=timedelta(hours=12),
        WTF_CSRF_TIME_LIMIT=12 * 60 * 60,
        STORAGE_PATH=e.get("STORAGE_PATH", "/tmp/codebuddy-source"),
        REDIS_URL=e.get("REDIS_URL", "redis://localhost:6379/0"),
        CELERY_BROKER_URL=e.get("CELERY_BROKER_URL", "redis://localhost:6379/1"),
        CELERY_RESULT_BACKEND=e.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/2"),
        GEMINI_API_KEY=e.get("GEMINI_API_KEY", ""),
        GEMINI_GENERATION_MODEL=e.get("GEMINI_GENERATION_MODEL", "gemini-3.5-flash"),
        GEMINI_EMBEDDING_MODEL=e.get("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001"),
    )
    for key, default in dict(
        MAX_UPLOAD_MB=100,
        MAX_EXPANDED_MB=500,
        MAX_ARCHIVE_ENTRIES=50000,
        MAX_INDEXED_FILES=2000,
        MAX_FILE_BYTES=1048576,
        MAX_CHUNKS_PER_PROJECT=10000,
        MAX_CONTEXT_TOKENS=10000,
        MAX_EMBEDDING_TOKENS_PER_SNAPSHOT=1000000,
        MAX_QUESTION_CHARS=6000,
        AI_TIMEOUT_SECONDS=60,
        AI_MAX_RETRIES=2,
        EMBEDDING_BATCH_DELAY_SECONDS=10,
        EMBEDDING_DIMENSIONS=768,
    ).items():
        cfg[key] = int(e.get(key, default))
        if cfg[key] <= 0:
            raise ValueError(f"{key} must be positive")
    if cfg["EMBEDDING_DIMENSIONS"] != 768:
        raise ValueError("This schema uses vector(768); migrate and reindex to change dimensions")
    if e.get("APP_ENV") == "production" and len(cfg["SECRET_KEY"]) < 32:
        raise ValueError("Set APP_SECRET_KEY to at least 32 random characters")
    if e.get("APP_ENV") == "production" and cfg["SECRET_KEY"].startswith("development-"):
        raise ValueError("Production requires APP_SECRET_KEY")
    cfg["MAX_CONTENT_LENGTH"] = cfg["MAX_UPLOAD_MB"] * 1024 * 1024 + 65536
    cfg["RATELIMIT_STORAGE_URI"] = cfg["REDIS_URL"]
    return cfg
