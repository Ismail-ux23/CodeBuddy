from flask import Blueprint, jsonify, request, session
from services.scoring import score_quiz
from models import Submission

api = Blueprint("quiz", __name__)

@api.post("/login")
def login():
    # Demonstration identity only; never use this as production authentication.
    name = (request.get_json(silent=True) or {}).get("name", "").strip()
    if not name:
        return jsonify(error="name required"), 400
    session["name"] = name
    return jsonify(name=name)

@api.post("/quizzes/<quiz_id>/submit")
def submit_quiz(quiz_id):
    if "name" not in session:
        return jsonify(error="sign in first"), 401
    answers = (request.get_json(silent=True) or {}).get("answers", {})
    if not isinstance(answers, dict):
        return jsonify(error="answers must be an object"), 400
    result = score_quiz(quiz_id, answers)
    if result is None:
        return jsonify(error="quiz not found"), 404
    submission = Submission(session["name"], quiz_id, result)
    return jsonify(submission.to_dict()), 201

@api.post("/logout")
def logout():
    session.clear()
    return jsonify(ok=True)
