import math
import random
import time
from google import genai
from google.genai import types, errors
from flask import current_app
from app.schemas import Answer
from app.rag.prompts import SYSTEM


def generation_schema():
    """Use the API's structural subset; enforce size limits locally with Answer."""
    schema = Answer.model_json_schema()
    definitions = schema.pop("$defs", {})

    def compatible(value):
        if isinstance(value, list):
            return [compatible(item) for item in value]
        if isinstance(value, dict):
            if "$ref" in value:
                return compatible(definitions[value["$ref"].split("/")[-1]])
            return {
                key: compatible(item) for key, item in value.items() if key not in {"title", "maxLength", "maxItems"}
            }
        return value

    return compatible(schema)


def public_failure_message(exc):
    """Return actionable provider failures without exposing provider payloads."""
    safe_failures = {
        "No indexable source remains": "No indexable source remains. Check the exclusion report, format files with very long lines, and upload again.",
        "Chunk quota exceeded": "Source exceeds the project's chunk limit. Exclude generated files or split the project before uploading again.",
        "Snapshot embedding token budget exceeded": "Source exceeds the embedding budget. Exclude generated files or split the project before uploading again.",
    }
    if isinstance(exc, ValueError) and str(exc) in safe_failures:
        return safe_failures[str(exc)]
    if isinstance(exc, errors.APIError):
        if exc.code in (500, 502, 503, 504):
            return "Gemini is temporarily unavailable or at capacity. Your project is saved. Retry this job in a few minutes."
        if exc.code == 429:
            return "Gemini's request or quota limit was reached. Check API usage and billing, then retry when quota is available."
        if exc.code in (401, 403):
            return "Gemini rejected access. Ask your administrator to check the API key and project permissions."
        if exc.code in (400, 404):
            return "Gemini rejected the configured model or request. Ask your administrator to check the model configuration."
    return "Processing failed. Check server configuration, provider limits, or excluded files, then retry."


class ProviderUnavailable(ValueError):
    pass


def retry_delay(exc, attempt):
    """Honor bounded provider backoff without echoing its payload."""
    details = exc.details if isinstance(exc.details, dict) else {}
    details = details.get("error", details).get("details", [])
    for detail in details:
        if not isinstance(detail, dict) or not str(detail.get("@type", "")).endswith("RetryInfo"):
            continue
        try:
            delay = float(str(detail.get("retryDelay", "")).removesuffix("s"))
        except ValueError:
            continue
        if math.isfinite(delay) and 0 <= delay <= 120:
            return max(delay + 1, 2**attempt)
    return 60 if exc.code == 429 else min(8, 2**attempt + random.random())


class Gemini:
    def __init__(self):
        self.cfg = current_app.config
        if not self.cfg["GEMINI_API_KEY"]:
            raise ProviderUnavailable("Configure GEMINI_API_KEY")
        self.client = genai.Client(
            api_key=self.cfg["GEMINI_API_KEY"],
            http_options=types.HttpOptions(timeout=self.cfg["AI_TIMEOUT_SECONDS"] * 1000),
        )

    def call(self, fn):
        for attempt in range(self.cfg["AI_MAX_RETRIES"] + 1):
            try:
                return fn()
            except errors.APIError as exc:
                if exc.code not in (429, 500, 502, 503, 504) or attempt == self.cfg["AI_MAX_RETRIES"]:
                    raise
                time.sleep(retry_delay(exc, attempt))

    def embed(self, texts, query=False):
        response = self.call(
            lambda: self.client.models.embed_content(
                model=self.cfg["GEMINI_EMBEDDING_MODEL"],
                contents=texts,
                config=types.EmbedContentConfig(
                    task_type="CODE_RETRIEVAL_QUERY" if query else "RETRIEVAL_DOCUMENT", output_dimensionality=768
                ),
            )
        )
        vectors = [x.values for x in response.embeddings or []]
        if len(vectors) != len(texts):
            raise ValueError("Embedding count mismatch")
        result = []
        for v in vectors:
            if not v or len(v) != 768 or not all(math.isfinite(x) for x in v):
                raise ValueError("Embedding shape mismatch")
            norm = math.sqrt(sum(x * x for x in v))
            if norm == 0:
                raise ValueError("Zero embedding")
            result.append([x / norm for x in v])
        return result

    def generate(self, payload):
        response = self.call(
            lambda: self.client.models.generate_content(
                model=self.cfg["GEMINI_GENERATION_MODEL"],
                contents=payload,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM,
                    response_mime_type="application/json",
                    response_schema=generation_schema(),
                    temperature=0.2,
                    max_output_tokens=8192,
                ),
            )
        )
        answer = Answer.model_validate_json(response.text)
        usage = response.usage_metadata.model_dump(mode="json") if response.usage_metadata else {}
        return answer, usage
