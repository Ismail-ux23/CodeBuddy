import json
from pathlib import Path
from flask import Blueprint, jsonify, abort, request, send_file

demo = Blueprint("demo", __name__)
ROOT = Path(__file__).resolve().parents[3] / "demo"


def manifest():
    return json.loads((ROOT / "manifest.json").read_text())


@demo.get("/manifest")
def demo_manifest():
    return jsonify(manifest())


@demo.get("/files")
def demo_files():
    files = manifest()["files"]
    ident = request.args.get("file_id")
    if not ident:
        return jsonify(items=files)
    f = next((f for f in files if f["id"] == ident), None)
    if not f:
        abort(404)
    return jsonify(**f, text=(ROOT / "repository" / f["relative_path"]).read_text())


@demo.get("/questions")
def questions():
    return jsonify(
        items=[
            dict(id=p.stem, question=json.loads(p.read_text())["question"])
            for p in sorted((ROOT / "answers").glob("*.json"))
        ]
    )


@demo.get("/answers/<ident>")
def answer(ident):
    if ident not in {"submission", "auth", "purpose", "onboarding"}:
        abort(404)
    return jsonify(json.loads((ROOT / "answers" / f"{ident}.json").read_text()))


@demo.get("/archive")
def archive():
    return send_file(ROOT / "quiz-garden.zip", as_attachment=True, download_name="quiz-garden.zip")
