import math
from types import SimpleNamespace
import pytest
from app.providers.gemini import Gemini


def provider_with(vectors):
    provider = Gemini.__new__(Gemini)
    provider.cfg = {"AI_MAX_RETRIES": 1, "GEMINI_EMBEDDING_MODEL": "gemini-embedding-001"}
    provider.client = SimpleNamespace(
        models=SimpleNamespace(
            embed_content=lambda **kwargs: SimpleNamespace(embeddings=[SimpleNamespace(values=v) for v in vectors])
        )
    )
    return provider


def test_provider_normalizes_reduced_dimensions():
    vector = provider_with([[2.0] * 768]).embed(["source"])[0]
    assert len(vector) == 768
    assert math.isclose(sum(x * x for x in vector), 1.0)


@pytest.mark.parametrize("vectors", [[[1.0] * 3], [[0.0] * 768], [[float("nan")] * 768], []])
def test_provider_rejects_invalid_embeddings(vectors):
    with pytest.raises(ValueError):
        provider_with(vectors).embed(["source"])


def test_generation_schema_compatibility_preserves_local_limits():
    import json
    from pydantic import ValidationError
    from app.providers.gemini import generation_schema
    from app.schemas import Answer

    schema = generation_schema()
    encoded = json.dumps(schema)
    assert all(key not in encoded for key in ['"$ref"', '"maxLength"', '"maxItems"'])
    claim = schema["properties"]["claims"]["items"]
    assert claim["properties"]["evidence_kind"]["enum"] == ["observed", "inferred", "general"]
    assert set(claim["required"]) == {"text", "evidence_kind", "source_ids"}
    with pytest.raises(ValidationError):
        Answer.model_validate(
            dict(
                answer_status="answered",
                claims=[dict(text="x" * 8001, evidence_kind="observed", source_ids=["sample"])],
                limitations=[],
                follow_up_questions=[],
            )
        )


@pytest.mark.parametrize(
    "code,expected",
    [
        (503, "temporarily unavailable"),
        (429, "quota limit"),
        (403, "project permissions"),
        (400, "model configuration"),
    ],
)
def test_public_provider_error_is_actionable_and_redacted(code, expected):
    from google.genai.errors import APIError
    from app.providers.gemini import public_failure_message

    message = public_failure_message(APIError(code, {"error": {"message": "private-provider-payload"}}))
    assert expected in message
    assert "private-provider-payload" not in message


@pytest.mark.parametrize("delay,expected", [("45s", 46), ("bad", 60), ("999999s", 60), ("NaNs", 60)])
def test_quota_backoff_respects_bounded_provider_delay(delay, expected):
    from google.genai.errors import APIError
    from app.providers.gemini import retry_delay

    error = APIError(
        429, {"error": {"details": [{"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": delay}]}}
    )
    assert retry_delay(error, 0) == expected
