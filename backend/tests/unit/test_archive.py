import io
import stat
import zipfile
import pytest
from app.ingestion.archive import inspect_zip, UnsafeArchive, sanitize

CFG = dict(
    MAX_UPLOAD_MB=25, MAX_EXPANDED_MB=100, MAX_ARCHIVE_ENTRIES=5000, MAX_FILE_BYTES=1048576, MAX_INDEXED_FILES=2000
)


def archive(entries, compression=zipfile.ZIP_STORED):
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", compression) as z:
        for path, data in entries:
            z.writestr(path, data)
    return out.getvalue()


def test_long_line_excluded_without_losing_other_source():
    files, report = inspect_zip(
        archive(
            [
                ("main.py", "print(42)"),
                ("app.css", "x" * 24548),
            ]
        ),
        CFG,
    )
    assert [f["path"] for f in files] == ["main.py"]
    excluded = next(row for row in report if row["path"] == "app.css")
    assert excluded["included"] is False
    assert "12,000" in excluded["reason"]


def test_only_long_lines_has_clear_upload_error():
    with pytest.raises(UnsafeArchive, match="No supported source files"):
        inspect_zip(archive([("app.css", "x" * 24548)]), CFG)


@pytest.mark.parametrize(
    "path", ["../escape.py", "/root.py", "C:/evil.py", "a/../../b.py", "a\\..\\evil.py", "a/bad.py"]
)
def test_traversal(path):
    with pytest.raises(UnsafeArchive):
        inspect_zip(archive([(path, "print(1)")]), CFG)


@pytest.mark.parametrize("path", ["nested.zip", "a.tar", "b.gz", "c.7z"])
def test_nested(path, monkeypatch):
    data = archive([(path, "not opened"), ("main.py", "print(42)")])
    original = zipfile.ZipFile.open

    def guarded_open(self, name, *args, **kwargs):
        filename = name.filename if isinstance(name, zipfile.ZipInfo) else name
        assert filename != path, "Nested archives must never be opened"
        return original(self, name, *args, **kwargs)

    monkeypatch.setattr(zipfile.ZipFile, "open", guarded_open)
    files, report = inspect_zip(data, CFG)
    assert [f["path"] for f in files] == ["main.py"]
    assert next(row for row in report if row["path"] == path) == {
        "path": path,
        "included": False,
        "reason": "nested archive skipped (not extracted)",
    }


def test_nested_only_zip_reports_no_supported_source():
    with pytest.raises(UnsafeArchive, match="No supported source files"):
        inspect_zip(archive([("project.zip", archive([("main.py", "print(42)")]))]), CFG)


def test_duplicates():
    with pytest.raises(UnsafeArchive):
        inspect_zip(archive([("x.py", "a"), ("X.py", "b")]), CFG)


def test_unicode_duplicates():
    with pytest.raises(UnsafeArchive):
        inspect_zip(archive([("é.py", "a"), ("é.py", "b")]), CFG)


@pytest.mark.parametrize("kind", [stat.S_IFLNK, stat.S_IFIFO, stat.S_IFSOCK, stat.S_IFCHR, stat.S_IFBLK])
def test_links_and_special_entries_are_skipped(kind, monkeypatch):
    link = zipfile.ZipInfo(".gitignore")
    link.create_system = 3
    link.external_attr = (kind | 0o777) << 16
    data = archive([(link, "*"), ("main.py", "print(42)")])
    original = zipfile.ZipFile.open

    def guarded_open(self, name, *args, **kwargs):
        filename = name.filename if isinstance(name, zipfile.ZipInfo) else name
        assert filename != ".gitignore", "Excluded entry must never be read, even as ignore rules"
        return original(self, name, *args, **kwargs)

    monkeypatch.setattr(zipfile.ZipFile, "open", guarded_open)
    files, report = inspect_zip(data, CFG)
    assert [f["path"] for f in files] == ["main.py"]
    skipped = next(row for row in report if row["path"] == ".gitignore")
    assert not skipped["included"]
    assert skipped["reason"] == ("symbolic link skipped" if kind == stat.S_IFLNK else "special file skipped")


def test_links_only_zip_has_no_supported_source():
    link = zipfile.ZipInfo("link.py")
    link.create_system = 3
    link.external_attr = (stat.S_IFLNK | 0o777) << 16
    with pytest.raises(UnsafeArchive, match="No supported source files"):
        inspect_zip(archive([(link, "../../outside.py")]), CFG)


def test_bomb():
    with pytest.raises(UnsafeArchive):
        inspect_zip(archive([("big.py", "a" * 100000)], zipfile.ZIP_DEFLATED), CFG)


def test_entry_limit():
    with pytest.raises(UnsafeArchive):
        inspect_zip(archive([("a.py", "1"), ("b.py", "2")]), dict(CFG, MAX_ARCHIVE_ENTRIES=1))


def test_expanded_limit():
    with pytest.raises(UnsafeArchive):
        inspect_zip(archive([("big.py", "x" * 1100000)]), dict(CFG, MAX_EXPANDED_MB=1))


def test_invalid_zip():
    with pytest.raises(UnsafeArchive):
        inspect_zip(b"not zip", CFG)


def test_empty():
    with pytest.raises(UnsafeArchive):
        inspect_zip(archive([("photo.png", b"binary")]), CFG)


def test_secrets_and_exclusions():
    files, report = inspect_zip(
        archive(
            [
                (".env", "PASSWORD=hidden"),
                ("src/a.py", 'api_key = "hidden"\nprint(1)\n'),
                ("node_modules/b.py", "bad"),
                ("README.md", "hello"),
            ]
        ),
        CFG,
    )
    assert {f["path"] for f in files} == {"src/a.py", "README.md"}
    assert "hidden" not in str(files)
    assert files[0]["text"].count("\n") == 2
    assert len(report) == 4


def test_private_key():
    assert sanitize("a.py", "-----BEGIN RSA PRIVATE KEY-----\nsecret")[0] is None


def test_env_example_names_only():
    clean, _ = sanitize(".env.example", "KEY=hidden\nPORT=5432\n")
    assert clean == "KEY=[REDACTED]\nPORT=[REDACTED]\n"


def test_gitignore_and_user_patterns():
    files, _ = inspect_zip(
        archive([(".gitignore", "ignored.py"), ("ignored.py", "1"), ("secret.py", "2"), ("keep.py", "3")]),
        CFG,
        ["secret.py"],
    )
    assert "ignored.py" not in [f["path"] for f in files]
    assert "secret.py" not in [f["path"] for f in files]


def test_actual_text_utf8_and_binary():
    files, report = inspect_zip(archive([("a.py", "hello"), ("b.py", b"\xff"), ("c.py", b"x\x00y")]), CFG)
    assert len(files) == 1
    assert len(report) == 3


def test_dependency_heavy_zip_above_old_entry_limit():
    from app.config import settings

    entries = [(f"project/node_modules/package/file{i}.js", "export default 1;") for i in range(5001)]
    entries.append(("project/main.py", "print(42)"))
    cfg = {**CFG, "MAX_ARCHIVE_ENTRIES": settings()["MAX_ARCHIVE_ENTRIES"]}
    files, report = inspect_zip(archive(entries), cfg)
    assert [f["path"] for f in files] == ["project/main.py"]
    assert sum(not row["included"] for row in report) == 5001


def test_entry_limit_error_reports_count_and_remedy():
    with pytest.raises(UnsafeArchive, match="contains 2 entries; the limit is 1") as exc:
        inspect_zip(archive([("a.py", "1"), ("b.py", "2")]), dict(CFG, MAX_ARCHIVE_ENTRIES=1))
    assert "node_modules" in str(exc.value)


@pytest.mark.parametrize("filename", ["main.py", ".gitignore"])
def test_corrupt_member_is_actionable_validation_error(filename):
    data = bytearray(archive([(filename, "unique-file-contents"), ("other.py", "print(1)")]))
    # Alter the payload while retaining the central directory's original CRC.
    data[data.index(b"unique-file-contents")] ^= 1
    with pytest.raises(UnsafeArchive, match="Re-create the ZIP"):
        inspect_zip(bytes(data), CFG)
