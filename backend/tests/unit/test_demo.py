import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3] / "demo"


def test_demo_citations():
    manifest = json.loads((ROOT / "manifest.json").read_text())
    for path in (ROOT / "answers").glob("*.json"):
        answer = json.loads(path.read_text())
        assert answer["label"] == "Precomputed demo answer"
        for c in answer["citations"]:
            assert c["snapshot_id"] == manifest["snapshot_id"]
            lines = (ROOT / "repository" / c["path"]).read_text().splitlines()
            assert 1 <= c["start_line"] <= c["end_line"] <= len(lines)
