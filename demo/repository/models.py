from dataclasses import dataclass

@dataclass(frozen=True)
class Submission:
    learner: str
    quiz_id: str
    score: dict

    def to_dict(self):
        return {"learner": self.learner, "quiz_id": self.quiz_id, "score": self.score}
