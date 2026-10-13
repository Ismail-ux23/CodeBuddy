import json
import zipfile
from pathlib import Path
root = Path(__file__).resolve().parents[1]
manifest = json.loads((root / "demo/manifest.json").read_text())
files = {f["id"]: f for f in manifest["files"]}
count = 0
for p in (root / "demo/answers").glob("*.json"):
    answer = json.loads(p.read_text())
    for c in answer["citations"]:
        f = files[c["file_id"]]
        assert c["snapshot_id"] == manifest["snapshot_id"]
        assert f["relative_path"] == c["path"]
        assert 1 <= c["start_line"] <= c["end_line"] <= len((root / "demo/repository" / c["path"]).read_text().splitlines())
        count += 1
with zipfile.ZipFile(root / "demo/quiz-garden.zip") as archive:
    for f in files.values():
        assert archive.read(f["relative_path"]).decode() == (root / "demo/repository" / f["relative_path"]).read_text()
print(f"Verified {len(files)} demo files and {count} citation ranges; ZIP matches source.")
