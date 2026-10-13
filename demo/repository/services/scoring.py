ANSWER_KEYS = {"python-basics": {"q1": "list", "q2": "def", "q3": "None"}}

def score_quiz(quiz_id, answers):
    key = ANSWER_KEYS.get(quiz_id)
    if key is None:
        return None
    correct = sum(answers.get(question) == expected for question, expected in key.items())
    return {"correct": correct, "total": len(key), "percentage": round(100 * correct / len(key), 1)}
