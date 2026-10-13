"""Read bounded ZIP members in memory; never extract user paths to disk."""

import hashlib
import io
import re
import stat
import unicodedata
import zipfile
import zlib
from pathlib import PurePosixPath
import pathspec
from app.ingestion.chunks import MAX_CHUNK_CHARACTERS, LONG_LINE_REASON


class UnsafeArchive(ValueError):
    pass


SKIP = {".git", "node_modules", "vendor", "venv", ".venv", "__pycache__", "build", "dist", ".next", "coverage"}
EXT = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".md",
    ".mdx",
    ".txt",
    ".html",
    ".css",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".sql",
}
ARCHIVES = {".zip", ".tar", ".gz", ".tgz", ".7z", ".rar", ".bz2", ".xz"}
SECRET = re.compile(
    r"(?i)((?:api[_-]?key|secret|password|passwd|token|authorization|access[_-]?key)\s*[\"']?\s*[:=]\s*)([^\r\n,}]+)"
)
TOKEN = re.compile(
    r"(?:AIza[\w-]{30,}|(?:ghp_|github_pat_|sk-|sk_live_)[\w-]{16,}|AKIA[A-Z0-9]{16}|eyJ[\w-]+\.eyJ[\w-]+\.[\w-]+)"
)


def sanitize(path, text):
    if "-----BEGIN " in text and "PRIVATE KEY-----" in text:
        return None, "private key material"
    if PurePosixPath(path).name == ".env.example":
        text = "\n".join(
            (line.split("=", 1)[0] + "=[REDACTED]") if "=" in line else ("" if line.strip().startswith("#") else line)
            for line in text.split("\n")
        )
    clean = TOKEN.sub("[REDACTED]", SECRET.sub(lambda m: m[1] + "[REDACTED]", text))
    return clean, "credentials redacted" if clean != text else "included"


def read_member(archive, info, limit):
    try:
        with archive.open(info) as member:
            return member.read(limit)
    except (zipfile.BadZipFile, RuntimeError, NotImplementedError, EOFError, zlib.error) as exc:
        raise UnsafeArchive(f"Cannot read ZIP entry {info.filename!r}. Re-create the ZIP and try again.") from exc


def inspect_zip(data, cfg, exclusions=()):
    if len(data) > cfg["MAX_UPLOAD_MB"] * 1024**2:
        raise UnsafeArchive("ZIP exceeds upload limit")
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise UnsafeArchive("Upload a valid ZIP archive") from exc
    files, report, seen, expanded = [], [], set(), 0
    with archive:
        entries = archive.infolist()
        if len(entries) > cfg["MAX_ARCHIVE_ENTRIES"]:
            raise UnsafeArchive(
                f"This ZIP contains {len(entries):,} entries; the limit is {cfg['MAX_ARCHIVE_ENTRIES']:,}. "
                "Create a source-only ZIP without node_modules, .git, .venv, build outputs, or datasets. "
                "Files and folders both count toward this limit."
            )
        regular_entries = []
        for info in entries:
            path = unicodedata.normalize("NFC", info.filename.replace("\\", "/"))
            parts = PurePosixPath(path).parts
            if (
                not path
                or path.startswith("/")
                or re.match(r"^[A-Za-z]:", path)
                or ".." in parts
                or any(ord(c) < 32 for c in path)
            ):
                raise UnsafeArchive("Unsafe archive path")
            normalized = str(PurePosixPath(path)).rstrip("/")
            if normalized.casefold() in seen:
                raise UnsafeArchive("Duplicate or ambiguous archive path")
            seen.add(normalized.casefold())
            mode = info.external_attr >> 16
            kind = stat.S_IFMT(mode)
            if kind not in (0, stat.S_IFREG, stat.S_IFDIR):
                reason = "symbolic link skipped" if kind == stat.S_IFLNK else "special file skipped"
                report.append(dict(path=path, included=False, reason=reason))
                continue
            if info.flag_bits & 1:
                raise UnsafeArchive("Encrypted ZIPs are unsupported")
            if info.is_dir() or kind == stat.S_IFDIR:
                continue
            if PurePosixPath(path).suffix.lower() in ARCHIVES:
                report.append(dict(path=path, included=False, reason="nested archive skipped (not extracted)"))
                continue
            expanded += info.file_size
            if expanded > cfg["MAX_EXPANDED_MB"] * 1024**2:
                raise UnsafeArchive("Expanded ZIP exceeds limit")
            if info.file_size / max(1, info.compress_size) > 100:
                raise UnsafeArchive("Suspicious compression ratio")
            regular_entries.append(info)
        ignore_text = []
        for info in regular_entries:
            if PurePosixPath(info.filename).name == ".gitignore" and info.file_size < 65536:
                # Root patterns only: safe conservative interpretation, no negation handling surprises.
                if len(PurePosixPath(info.filename).parts) <= 2:
                    ignore_text += read_member(archive, info, 65536).decode("utf-8", errors="replace").splitlines()
        spec = pathspec.PathSpec.from_lines("gitwildmatch", ignore_text + list(exclusions))
        read_total = 0
        for info in regular_entries:
            if info.is_dir():
                continue
            path = unicodedata.normalize("NFC", info.filename.replace("\\", "/"))
            p = PurePosixPath(path)
            name = p.name.lower()
            reason = None
            if set(p.parts) & SKIP:
                reason = "dependency or generated directory"
            elif (
                (name.startswith(".env") and name != ".env.example")
                or any(x in name for x in ("credential", "id_rsa", "id_ed25519"))
                or p.suffix.lower() in {".pem", ".key", ".p12", ".pfx"}
            ):
                reason = "secret-bearing filename"
            elif spec.match_file(path) or spec.match_file("/".join(p.parts[1:])):
                reason = "excluded by pattern"
            elif info.file_size > cfg["MAX_FILE_BYTES"]:
                reason = "file too large"
            elif p.suffix.lower() not in EXT and name not in {"dockerfile", ".env.example", ".gitignore"}:
                reason = "unsupported or binary file"
            elif name.endswith((".min.js", ".map", "-lock.json")) or name in {"yarn.lock", "pnpm-lock.yaml"}:
                reason = "generated file"
            if reason:
                report.append(dict(path=path, included=False, reason=reason))
                continue
            raw = read_member(archive, info, cfg["MAX_FILE_BYTES"] + 1)
            read_total += len(raw)
            if len(raw) > cfg["MAX_FILE_BYTES"] or read_total > cfg["MAX_EXPANDED_MB"] * 1024**2:
                raise UnsafeArchive("Actual expanded bytes exceed limit")
            try:
                text = raw.decode("utf-8-sig")
            except UnicodeDecodeError:
                report.append(dict(path=path, included=False, reason="not UTF-8 text"))
                continue
            if "\x00" in text:
                report.append(dict(path=path, included=False, reason="binary content"))
                continue
            text, reason = sanitize(path, text)
            if text is None:
                report.append(dict(path=path, included=False, reason=reason))
                continue
            if not text.strip():
                report.append(dict(path=path, included=False, reason="empty file"))
                continue
            if any(len(line) > MAX_CHUNK_CHARACTERS for line in text.splitlines()):
                report.append(dict(path=path, included=False, reason=LONG_LINE_REASON))
                continue
            if len(files) >= cfg["MAX_INDEXED_FILES"]:
                raise UnsafeArchive("Too many supported files; exclude files and retry")
            files.append(
                dict(
                    path=path,
                    text=text,
                    language=p.suffix.lstrip(".") or "text",
                    hash=hashlib.sha256(text.encode()).hexdigest(),
                )
            )
            report.append(dict(path=path, included=True, reason=reason))
    if not files:
        raise UnsafeArchive("No supported source files remain after exclusions")
    return files, report
