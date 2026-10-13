from services.scoring import score_quiz

def test_full_score():
    result = score_quiz("python-basics", {"q1": "list", "q2": "def", "q3": "None"})
    assert result["percentage"] == 100.0

def test_missing_answers():
    assert score_quiz("python-basics", {})["correct"] == 0

def test_unknown_quiz():
    assert score_quiz("missing", {}) is None
