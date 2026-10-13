import io
import pytest
from .conftest import post, register, token
from app.extensions import db
from app.models import Snapshot, SourceFile, Conversation, Job, Guide
from app.services.storage import write_source

pytestmark = pytest.mark.integration


def test_csrf_and_auth(client):
    assert client.post("/api/v1/auth/login", json={}).status_code == 400
    assert client.get("/api/v1/projects").status_code == 401
    assert register(client, "one@example.com").status_code == 201
    assert client.get("/api/v1/projects").status_code == 200
    assert post(client, "/auth/logout", {}).status_code == 200
    assert client.get("/api/v1/projects").status_code == 401


def test_other_owner_cannot_read_nested_records(app, client):
    register(client, "one@example.com")
    p = post(client, "/projects", dict(name="Private")).json
    with app.app_context():
        s = Snapshot(id="snapshot", project_id=p["id"], status="ready")
        db.session.add(s)
        db.session.flush()
        f = SourceFile(
            id="file",
            snapshot_id=s.id,
            relative_path="private.py",
            language="py",
            storage_key=write_source(s.id, "file", "print(42)"),
            content_hash="a" * 64,
            line_count=1,
            size=9,
        )
        c = Conversation(id="conv", owner_id=p["owner_id"], project_id=p["id"], snapshot_id=s.id)
        j = Job(
            id="job",
            owner_id=p["owner_id"],
            project_id=p["id"],
            snapshot_id=s.id,
            kind="answer",
            idempotency_key="testing-key",
        )
        g = Guide(id="guide", project_id=p["id"], snapshot_id=s.id, content={})
        db.session.add_all([f, c, j, g])
        db.session.commit()
    other = app.test_client()
    register(other, "two@example.com")
    for path in [
        f"/projects/{p['id']}",
        f"/projects/{p['id']}/files?snapshot_id=snapshot",
        f"/projects/{p['id']}/files/file?snapshot_id=snapshot",
        "/uploads/snapshot",
        "/conversations/conv",
        "/conversations/conv/messages",
        "/jobs/job",
        "/jobs/job/events",
        "/guides/guide/export",
    ]:
        assert other.get("/api/v1" + path).status_code == 404, path


def test_no_key_is_explicit_and_source_preview_works(client):
    from tests.unit.test_archive import archive

    register(client, "one@example.com")
    p = post(client, "/projects", dict(name="Source")).json
    response = client.post(
        f"/api/v1/projects/{p['id']}/uploads",
        data={"file": (io.BytesIO(archive([("main.py", "print(42)\n")])), "source.zip")},
        headers={"X-CSRFToken": token(client)},
    )
    assert response.status_code == 201
    s = response.json
    files = client.get(f"/api/v1/projects/{p['id']}/files?snapshot_id={s['id']}").json["items"]
    source = client.get(f"/api/v1/projects/{p['id']}/files/{files[0]['id']}?snapshot_id={s['id']}")
    assert source.json["text"] == "print(42)"
    assert post(client, f"/uploads/{s['id']}/index", dict(consent=True)).status_code == 503


def test_private_demo_isolation(client):
    assert client.get("/api/v1/demo/files?file_id=arbitrary-private-file").status_code == 404
    assert client.get("/api/v1/demo/manifest").status_code == 200


def test_zip_above_old_limit_is_accepted(client):
    from tests.unit.test_archive import archive

    register(client, "large-upload@example.com")
    p = post(client, "/projects", {"name": "Large FYP repository"}).json
    # A stored, uncompressed asset makes the ZIP truly >25 MiB. It is excluded
    # from indexing while the supported source remains available for preview.
    data = archive([("main.py", "def hello():\n    return 42\n"), ("assets/demo.bin", b"\x00" * (32 * 1024 * 1024))])
    response = client.post(
        f"/api/v1/projects/{p['id']}/uploads",
        data={"file": (io.BytesIO(data), "fyp.zip")},
        headers={"X-CSRFToken": token(client)},
    )
    assert response.status_code == 201, response.json
    assert response.json["file_count"] == 1
    assert len(data) > 25 * 1024 * 1024


@pytest.mark.parametrize("password", [None, 123, [], {}])
def test_account_rejects_non_string_password(client, password):
    register(client, "account@example.com")
    response = client.patch("/api/v1/account", json={"password": password, "display_name": "New"},
                            headers={"X-CSRFToken": token(client)})
    assert response.status_code == 422


def test_password_spaces_are_significant(client):
    password = "  long-valid-password  "
    assert post(client, "/auth/register", dict(email="spaces@example.com", password=password,
                                             display_name="Spaces")).status_code == 201
    post(client, "/auth/logout", {})
    assert post(client, "/auth/login", dict(email="spaces@example.com", password=password.strip())).status_code == 401
    assert post(client, "/auth/login", dict(email="spaces@example.com", password=password)).status_code == 200
