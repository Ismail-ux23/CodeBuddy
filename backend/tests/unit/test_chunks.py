import pytest
from app.ingestion.chunks import chunks


@pytest.mark.parametrize(
    "language,text",
    [
        ("py", "import os\n\ndef hello():\n    return 42\n"),
        ("tsx", "export function App() { return <p>Hello</p>; }\n"),
        ("js", "function go() { return 1; }\n"),
        ("txt", "\n".join(str(i) for i in range(300))),
        ("md", "# Hello\nWorld\n## Next\nMore"),
    ],
)
def test_exact_lines(language, text):
    parts, status = chunks(text, language)
    assert parts
    for p in parts:
        assert p.start >= 1 and p.end <= len(text.splitlines())
        assert p.text == "\n".join(text.splitlines()[p.start - 1 : p.end])
        assert p.end - p.start < 80
    covered = {i for p in parts for i in range(p.start, p.end + 1)}
    assert all(i in covered for i, line in enumerate(text.splitlines(), 1) if line.strip())


def test_invalid_parse_fallback():
    parts, status = chunks("def broken(:\n    ???\n", "py")
    assert parts and status == "parse-warning"


def test_very_long_line_is_bounded():
    with pytest.raises(ValueError):
        chunks("x" * 13000, "txt")
