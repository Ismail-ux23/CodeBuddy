import io
import json
from types import SimpleNamespace
import pytest
from app.extensions import db
from app.models import Project, Snapshot, Chunk, Job
from app.schemas import Answer
from tests.unit.test_archive import archive
from .conftest import post, register, token

pytestmark = pytest.mark.integration


class FakeProvider:
    """Deterministic test double; never selected by production configuration."""

    def __init__(self):
        self.client = SimpleNamespace(close=lambda: None)

    def embed(self, texts, query=False):
        return [[1.0] + [0.0] * 767 for _ in texts]

    def generate(self, payload):
        data = json.loads(payload)
        if "candidate" in data:
            return Answer.model_validate({k: v for k, v in data["candidate"].items() if k != "citations"}), {}
        evidence = data["untrusted_evidence"]
        return Answer(
            answer_status="answered",
            claims=[
                dict(
                    text="The supplied source defines a function.",
                    evidence_kind="observed",
                    source_ids=[evidence[0]["source_id"]],
                )
            ],
            limitations=[],
            follow_up_questions=[],
        ), {}


def uploaded(app, client, entries=None):
    register(client, "pipeline@example.com")
    p = post(client, "/projects", dict(name="Pipeline")).json
    data = archive(entries if entries is not None else [("main.py", "def hello():\n    return 42\n")])
    s = client.post(
        f"/api/v1/projects/{p['id']}/uploads",
        data={"file": (io.BytesIO(data), "source.zip")},
        headers={"X-CSRFToken": token(client)},
    ).json
    app.config["GEMINI_API_KEY"] = "test-only-mock-key"
    j = client.post(
        f"/api/v1/uploads/{s['id']}/index",
        json={"consent": True},
        headers={"X-CSRFToken": token(client), "Idempotency-Key": "pipeline-test-key"},
    ).json
    return p, s, j


@pytest.mark.parametrize("keep_source", [True, False])
def test_existing_preview_with_long_lines(app, client, monkeypatch, keep_source):
    from app.tasks import worker
    from app.models import SourceFile
    from app.services.storage import file_path

    monkeypatch.setattr(worker, "flask_app", app)
    monkeypatch.setattr(worker, "Gemini", FakeProvider)
    entries = [("app.css", "body {}")]
    if keep_source:
        entries.append(("main.py", "print(42)"))
    p, s, j = uploaded(app, client, entries)
    # Simulate a preview stored before long-line validation was introduced.
    with app.app_context():
        f = db.session.scalar(db.select(SourceFile).where(SourceFile.relative_path == "app.css"))
        file_path(f.storage_key).write_text("x" * 24548)
    worker.run.run(j["id"])
    with app.app_context():
        job = db.session.get(Job, j["id"])
        snapshot = db.session.get(Snapshot, s["id"])
        assert next(r for r in snapshot.report if r["path"] == "app.css")["included"] is False
        if keep_source:
            assert job.status == "completed"
            assert db.session.get(Project, p["id"]).active_snapshot_id == s["id"]
            assert [c.text for c in db.session.scalars(db.select(Chunk))] == ["print(42)"]
        else:
            assert job.status == "failed"
            assert "No indexable source remains" in job.error_message
            assert db.session.get(Project, p["id"]).active_snapshot_id is None


def test_index_activation_redelivery_and_search(app, client, monkeypatch):
    from app.tasks import worker
    from app.rag.retrieval import retrieve

    monkeypatch.setattr(worker, "flask_app", app)
    monkeypatch.setattr(worker, "Gemini", FakeProvider)
    p, s, j = uploaded(app, client)
    worker.run.run(j["id"])
    with app.app_context():
        assert db.session.get(Project, p["id"]).active_snapshot_id == s["id"]
        assert db.session.get(Job, j["id"]).status == "completed"
        count = db.session.query(Chunk).count()
        assert count > 0
        result = retrieve(db.session.get(Snapshot, s["id"]), "hello", FakeProvider())
        assert next(iter(result.values()))["path"] == "main.py"
    worker.run.run(j["id"])
    with app.app_context():
        assert db.session.query(Chunk).count() == count


def test_cancelled_ingestion_does_not_activate(app, client, monkeypatch):
    from app.tasks import worker

    monkeypatch.setattr(worker, "flask_app", app)
    monkeypatch.setattr(worker, "Gemini", FakeProvider)
    p, s, j = uploaded(app, client)
    post(client, f"/jobs/{j['id']}/cancel", {})
    worker.run.run(j["id"])
    with app.app_context():
        assert db.session.get(Project, p["id"]).active_snapshot_id is None
        assert db.session.get(Job, j["id"]).status == "cancelled"


def test_deleted_project_is_not_resurrected(app, client, monkeypatch):
    from app.tasks import worker

    monkeypatch.setattr(worker, "flask_app", app)
    monkeypatch.setattr(worker, "Gemini", FakeProvider)
    p, s, j = uploaded(app, client)
    assert client.delete(f"/api/v1/projects/{p['id']}", headers={"X-CSRFToken": token(client)}).status_code == 200
    worker.run.run(j["id"])
    with app.app_context():
        assert db.session.get(Project, p["id"]) is None
        assert db.session.query(Chunk).count() == 0


def test_complete_answer_and_guide_flow(app, client, monkeypatch):
    """Real DB/session/source pipeline; only the paid provider is a test double."""
    from app.tasks import worker

    monkeypatch.setattr(worker, "flask_app", app)
    monkeypatch.setattr(worker, "Gemini", FakeProvider)
    p, s, ingestion = uploaded(app, client)
    worker.run.run(ingestion["id"])
    conversation = post(client, f"/projects/{p['id']}/conversations", {}).json
    response = client.post(
        f"/api/v1/conversations/{conversation['id']}/messages",
        json={"question": "What does hello do?"},
        headers={"X-CSRFToken": token(client), "Idempotency-Key": "answer-flow-key"},
    )
    assert response.status_code == 202
    job = response.json
    worker.run.run(job["id"])
    assert client.get(f"/api/v1/jobs/{job['id']}").json["status"] == "completed"
    messages = client.get(f"/api/v1/conversations/{conversation['id']}/messages").json["items"]
    assistant = next(m for m in messages if m["role"] == "assistant")
    assert assistant["content"]["answer_status"] == "answered"
    citation = assistant["content"]["citations"][0]
    assert citation["snapshot_id"] == s["id"]
    assert citation["path"] == "main.py"
    assert citation["start_line"] == 1
    assert post(client, f"/messages/{assistant['id']}/feedback", {"rating": 1}).status_code == 200
    worker.run.run(job["id"])
    again = client.get(f"/api/v1/conversations/{conversation['id']}/messages").json["items"]
    assert len(again) == len(messages)
    guide_job = client.post(
        f"/api/v1/projects/{p['id']}/guides",
        json={},
        headers={"X-CSRFToken": token(client), "Idempotency-Key": "guide-flow-key"},
    ).json
    worker.run.run(guide_job["id"])
    assert client.get(f"/api/v1/jobs/{guide_job['id']}").json["status"] == "completed"
    guides = client.get(f"/api/v1/projects/{p['id']}/guides").json["items"]
    assert len(guides) == 1
    exported = client.get(f"/api/v1/guides/{guides[0]['id']}/export")
    assert exported.status_code == 200
    assert "main.py" in exported.text and s["id"] in exported.text
    assert "attachment" in exported.headers["Content-Disposition"]


def test_provider_failure_keeps_previous_snapshot(app, client, monkeypatch):
    from app.tasks import worker

    monkeypatch.setattr(worker, "flask_app", app)
    monkeypatch.setattr(worker, "Gemini", FakeProvider)
    p, s, ingestion = uploaded(app, client)
    worker.run.run(ingestion["id"])
    replacement = client.post(
        f"/api/v1/projects/{p['id']}/uploads",
        data={"file": (io.BytesIO(archive([("main.py", "def updated():\n    return 100\n")])), "new.zip")},
        headers={"X-CSRFToken": token(client)},
    ).json
    queued = client.post(
        f"/api/v1/uploads/{replacement['id']}/index",
        json={"consent": True},
        headers={"X-CSRFToken": token(client), "Idempotency-Key": "replacement-key"},
    ).json

    class BrokenProvider(FakeProvider):
        def embed(self, texts, query=False):
            raise RuntimeError("Simulated provider outage")

    monkeypatch.setattr(worker, "Gemini", BrokenProvider)
    worker.run.run(queued["id"])
    with app.app_context():
        assert db.session.get(Project, p["id"]).active_snapshot_id == s["id"]
        assert db.session.get(Job, queued["id"]).status == "failed"
        assert db.session.get(Snapshot, s["id"]).status == "ready"


@pytest.mark.parametrize("change_model", [False, True])
def test_retry_reuses_only_matching_model_embeddings(app, client, monkeypatch, change_model):
    from app.tasks import worker

    class InterruptedProvider(FakeProvider):
        calls = 0
        successful = []

        def embed(self, texts, query=False):
            type(self).calls += 1
            if self.calls == 2:
                raise RuntimeError("Simulated quota interruption")
            self.successful.extend(texts)
            return super().embed(texts, query)

    monkeypatch.setattr(worker, "flask_app", app)
    monkeypatch.setattr(worker, "Gemini", InterruptedProvider)
    p, s, j = uploaded(app, client, [(f"file{i}.py", f"print({i})") for i in range(33)])
    worker.run.run(j["id"])
    assert len(InterruptedProvider.successful) == 16
    assert client.get(f"/api/v1/jobs/{j['id']}").json["status"] == "failed"
    if change_model:
        app.config["GEMINI_EMBEDDING_MODEL"] = "different-test-model"
    assert post(client, f"/jobs/{j['id']}/retry", {}).status_code == 202
    worker.run.run(j["id"])
    assert client.get(f"/api/v1/jobs/{j['id']}").json["status"] == "completed"
    assert len(InterruptedProvider.successful) == (49 if change_model else 33)
    with app.app_context():
        assert db.session.get(Project, p["id"]).active_snapshot_id == s["id"]
        assert db.session.query(Chunk).count() == 33


def test_failed_delivery_requires_explicit_retry(app, client, monkeypatch):
    from app.tasks import worker

    monkeypatch.setattr(worker, "flask_app", app)
    p, s, j = uploaded(app, client)

    class BrokenProvider(FakeProvider):
        def embed(self, texts, query=False):
            raise RuntimeError("Provider outage")

    monkeypatch.setattr(worker, "Gemini", BrokenProvider)
    worker.run.run(j["id"])
    monkeypatch.setattr(worker, "Gemini", FakeProvider)
    worker.run.run(j["id"])
    with app.app_context():
        failed = db.session.get(Job, j["id"])
        assert failed.status == "failed"
        assert failed.attempt == 1
        assert db.session.get(Project, p["id"]).active_snapshot_id is None
    assert post(client, f"/jobs/{j['id']}/retry", {}).status_code == 202
    assert client.get(f"/api/v1/uploads/{s['id']}").json["status"] == "queued"
    assert client.delete(f"/api/v1/uploads/{s['id']}", headers={"X-CSRFToken": token(client)}).status_code == 409
    worker.run.run(j["id"])
    assert client.get(f"/api/v1/jobs/{j['id']}").json["status"] == "completed"
