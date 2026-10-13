"""Opt-in browser acceptance: real isolated DB, Redis and worker; test-only AI.
Run via scripts/local_run.py --test .venv/bin/python -m tests.browser_flow.
Set CODEBUDDY_LIVE_TEST=1 to use real Gemini on the synthetic fixture (billable API calls).
Never runs against the application database. Requires frontend on port 3000.
"""

import os
import subprocess
import tempfile
import threading
from pathlib import Path

live = os.environ.get("CODEBUDDY_LIVE_TEST") == "1"
if live and not os.environ.get("GEMINI_API_KEY"):
    raise SystemExit("Live acceptance requires GEMINI_API_KEY")
url = os.environ.get("TEST_DATABASE_URL", "")
if "test" not in url.rsplit("/", 1)[-1]:
    raise SystemExit("An explicit test database is required")
os.environ["DATABASE_URL"] = url
os.environ["CELERY_BROKER_URL"] = "redis://127.0.0.1:56379/5"
os.environ["CELERY_RESULT_BACKEND"] = "redis://127.0.0.1:56379/6"

from celery.contrib.testing.worker import start_worker
from sqlalchemy import text
from werkzeug.serving import make_server
from app import create_app
from app.extensions import db
from app.tasks import worker
from tests.integration.test_pipeline import FakeProvider
from tests.unit.test_archive import archive

root = Path(__file__).resolve().parents[2]
with tempfile.TemporaryDirectory(prefix="codebuddy-browser-") as storage:
    app = create_app(
        dict(
            TESTING=True,
            SQLALCHEMY_DATABASE_URI=url,
            REDIS_URL="redis://127.0.0.1:56379/7",
            RATELIMIT_ENABLED=False,
            STORAGE_PATH=storage,
            GEMINI_API_KEY=os.environ["GEMINI_API_KEY"] if live else "test-only-no-network",
        )
    )
    worker.flask_app = app
    if not live:
        worker.Gemini = FakeProvider
    with app.app_context():
        db.session.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        db.session.commit()
        db.drop_all()
        db.create_all()
    zip_path = Path(storage) / "fixture.zip"
    zip_path.write_bytes(archive([("main.py", "def hello():\n    return 42\n")]))
    server = make_server("127.0.0.1", 5099, app, threaded=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    stop = threading.Event()

    def dispatch():
        while not stop.wait(0.5):
            worker.dispatch.run()

    dispatcher = threading.Thread(target=dispatch, daemon=True)
    try:
        with start_worker(worker.celery, pool="solo", perform_ping_check=False):
            dispatcher.start()
            result = subprocess.run(
                ["node", "tests/private-flow.mjs"],
                cwd=root / "frontend",
                env={**os.environ, "FLOW_ZIP": str(zip_path)},
                timeout=480 if live else 240,
            )
            if result.returncode:
                raise SystemExit(result.returncode)
    finally:
        stop.set()
        dispatcher.join(timeout=5)
        server.shutdown()
        with app.app_context():
            db.session.remove()
            db.drop_all()
