import hashlib
from dataclasses import dataclass
from tree_sitter import Language, Parser
import tree_sitter_python
import tree_sitter_javascript
import tree_sitter_typescript

MAX_CHUNK_CHARACTERS = 12000
LONG_LINE_REASON = "source line exceeds 12,000 characters; format this file before indexing"


class SourceLineTooLong(ValueError):
    pass


@dataclass
class Piece:
    start: int
    end: int
    text: str
    symbol: str | None


LANGUAGES = {
    "py": tree_sitter_python.language,
    "js": tree_sitter_javascript.language,
    "jsx": tree_sitter_javascript.language,
    "ts": tree_sitter_typescript.language_typescript,
    "tsx": tree_sitter_typescript.language_tsx,
}


def chunks(text, language, window=80):
    lines = text.splitlines()
    if not lines:
        return [], "empty"
    if any(len(line) > MAX_CHUNK_CHARACTERS for line in lines):
        raise SourceLineTooLong(LONG_LINE_REASON)
    boundaries = {1, len(lines) + 1}
    symbols = {}
    status = "line-fallback"
    if language in LANGUAGES:
        try:
            tree = Parser(Language(LANGUAGES[language]())).parse(text.encode())
            status = "parsed" if not tree.root_node.has_error else "parse-warning"
            for node in tree.root_node.children:
                start = node.start_point.row + 1
                boundaries.add(start)
                name = node.child_by_field_name("name")
                if name:
                    symbols[start] = name.text.decode()[:250]
        except (ValueError, RuntimeError):
            status = "line-fallback"
    elif language in {"md", "mdx"}:
        boundaries.update(i + 1 for i, line in enumerate(lines) if line.startswith("#"))
    ordered = sorted(boundaries)
    result = []
    for a, b in zip(ordered, ordered[1:]):
        start = a
        while start < b:
            end = min(start + window - 1, b - 1)
            # Bound very long lines separately at ingestion: never silently mislabel source ranges.
            content = "\n".join(lines[start - 1 : end])
            if len(content) > MAX_CHUNK_CHARACTERS:
                while len(content) > MAX_CHUNK_CHARACTERS and end > start:
                    end -= 1
                    content = "\n".join(lines[start - 1 : end])
            if content.strip():
                result.append(Piece(start, end, content, symbols.get(a)))
            start = end + 1 if end == b - 1 else max(start + 1, end - 5)
    return result, status


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()
