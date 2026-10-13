import os
import pytest
from sqlalchemy import text
from app import create_app
from app.extensions import db


@pytest.fixture()
def app(tmp_path):
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set TEST_DATABASE_URL and TEST_REDIS_URL for real integration tests")
    if "test" not in url.rsplit("/", 1)[-1]:
        raise RuntimeError("Integration database name must contain test")
    app = create_app(
        dict(
            TESTING=True,
            SQLALCHEMY_DATABASE_URI=url,
            REDIS_URL=os.environ.get("TEST_REDIS_URL", "redis://localhost:6379/4"),
            RATELIMIT_ENABLED=False,
            STORAGE_PATH=str(tmp_path),
            GEMINI_API_KEY="",
            EMBEDDING_BATCH_DELAY_SECONDS=0,
        )
    )
    with app.app_context():
        db.session.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        db.session.commit()
        db.drop_all()
        db.create_all()
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def token(client):
    return client.get("/api/v1/auth/csrf").json["csrf_token"]


def post(client, path, data):
    return client.post("/api/v1" + path, json=data, headers={"X-CSRFToken": token(client)})


def register(client, email):
    return post(client, "/auth/register", dict(email=email, password="long-valid-password", display_name="Test"))
