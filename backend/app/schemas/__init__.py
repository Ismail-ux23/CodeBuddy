from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, EmailStr, StringConstraints, model_validator

Password = Annotated[str, StringConstraints(strip_whitespace=False)]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Register(Input):
    email: EmailStr
    password: Password = Field(min_length=12, max_length=128)
    display_name: str = Field(min_length=1, max_length=100)


class Login(Input):
    email: EmailStr
    password: Password = Field(min_length=1, max_length=128)


class ProjectInput(Input):
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=2000)


class Question(Input):
    question: str = Field(min_length=1, max_length=6000)
    file_id: str | None = None
    start_line: int | None = Field(default=None, ge=1)
    end_line: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def validate_selection(self):
        if (self.start_line is None) != (self.end_line is None):
            raise ValueError("Provide both start_line and end_line")
        if self.start_line is not None:
            if not self.file_id:
                raise ValueError("A line selection requires file_id")
            if self.start_line > self.end_line:
                raise ValueError("start_line must not exceed end_line")
        return self


class Claim(BaseModel):
    text: str = Field(max_length=8000)
    evidence_kind: Literal["observed", "inferred", "general"]
    source_ids: list[str] = Field(max_length=20)


class Answer(BaseModel):
    answer_status: Literal["answered", "partial", "insufficient_evidence"]
    claims: list[Claim] = Field(max_length=30)
    limitations: list[str] = Field(max_length=15)
    follow_up_questions: list[str] = Field(max_length=6)
