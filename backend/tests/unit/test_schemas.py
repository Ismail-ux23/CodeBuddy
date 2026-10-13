import pytest
from pydantic import ValidationError
from app.schemas import Login, Register, Question


def test_password_whitespace_is_preserved():
    password = "  long-password  "
    assert Register(email="me@example.com", password=password, display_name=" Me ").password == password
    assert Login(email="me@example.com", password=password).password == password
    assert Register(email="me@example.com", password=password, display_name=" Me ").display_name == "Me"


@pytest.mark.parametrize("selection", [
    {"file_id": "f", "start_line": 2},
    {"file_id": "f", "end_line": 3},
    {"start_line": 1, "end_line": 2},
    {"file_id": "f", "start_line": 3, "end_line": 2},
])
def test_incomplete_or_reversed_line_selection_is_rejected(selection):
    with pytest.raises(ValidationError):
        Question(question="Explain this", **selection)


def test_complete_line_selection_is_accepted():
    q = Question(question="Explain this", file_id="f", start_line=2, end_line=3)
    assert (q.start_line, q.end_line) == (2, 3)
