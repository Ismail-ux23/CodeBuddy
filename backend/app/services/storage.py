from pathlib import Path
from flask import current_app
import shutil


def root():
    p = Path(current_app.config["STORAGE_PATH"]).resolve()
    p.mkdir(parents=True, exist_ok=True, mode=0o700)
    return p


def file_path(key):
    p = (root() / key).resolve()
    if root() not in p.parents:
        raise ValueError("Invalid storage key")
    return p


def write_source(snapshot_id, file_id, text):
    key = f"{snapshot_id}/{file_id}.txt"
    p = file_path(key)
    p.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    p.chmod(0o600)
    return key


def remove_snapshot(sid):
    p = file_path(sid)
    if p.exists():
        shutil.rmtree(p)
