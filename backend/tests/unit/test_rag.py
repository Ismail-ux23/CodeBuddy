import pytest
from app.schemas import Answer
from app.rag.citations import validate_answer
from app.rag.retrieval import rrf


def answer(ids, kind="observed"):
    return Answer(
        answer_status="answered",
        claims=[dict(text="A claim", evidence_kind=kind, source_ids=ids)],
        limitations=[],
        follow_up_questions=[],
    )


E = {"c1": dict(source_id="c1", file_id="f1", snapshot_id="s1", path="a.py", start_line=2, end_line=4, line_count=5)}


def test_unknown_source_is_removed():
    result = validate_answer(answer(["made-up"]), E)
    assert result["answer_status"] == "insufficient_evidence" and not result["claims"]


def test_missing_source_is_removed():
    assert validate_answer(answer([]), E)["answer_status"] == "insufficient_evidence"


def test_general_explanation_can_have_no_source():
    assert len(validate_answer(answer([], "general"), E)["claims"]) == 1


def test_exact_server_range():
    result = validate_answer(answer(["c1"]), E)
    assert result["citations"][0]["start_line"] == 2
    assert result["citations"][0]["snapshot_id"] == "s1"


def test_bad_server_range():
    with pytest.raises(ValueError):
        validate_answer(answer(["c1"]), {"c1": dict(E["c1"], end_line=9)})


def test_rrf_rewards_multiple_rankings():
    assert rrf(["a", "b", "c"], ["b", "c", "d"])[0] == "b"
