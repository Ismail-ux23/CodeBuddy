from typing import Protocol
from app.schemas import Answer


class CodeProvider(Protocol):
    def embed(self, texts: list[str], query: bool = False) -> list[list[float]]: ...
    def generate(self, payload: str) -> tuple[Answer, dict]: ...
