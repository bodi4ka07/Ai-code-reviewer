import uuid
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional
from app.agent.tools.github_fetcher import parse_github_url
from app.core.config import settings
from app.core.languages import normalize_language
from app.models.review import ReviewStatus
from app.schemas.comment import CommentResponse


class ReviewCreate(BaseModel):
    project_id: uuid.UUID
    code_snippet: Optional[str] = Field(default=None, max_length=settings.MAX_CODE_CHARS)
    github_url: Optional[str] = Field(default=None, max_length=500)
    # Якщо не вказано: визначається за посиланням GitHub, інакше береться мова проєкту
    language: Optional[str] = None

    @field_validator("language")
    @classmethod
    def check_language(cls, v: Optional[str]) -> Optional[str]:
        return normalize_language(v) if v is not None else None

    @model_validator(mode="after")
    def check_source_provided(self):
        if not self.code_snippet and not self.github_url:
            raise ValueError("Потрібно надати або code_snippet або github_url")
        if not self.code_snippet and self.github_url:
            parse_github_url(self.github_url)  # ValueError -> 422
        return self


class ReviewResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    language: str
    status: ReviewStatus
    overall_score: Optional[int]
    summary: Optional[str]
    error_message: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]

    model_config = {"from_attributes": True}


class QuestionResponse(BaseModel):
    id: uuid.UUID
    comment_id: Optional[uuid.UUID]
    question: str
    answer: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ReviewDetailResponse(ReviewResponse):
    code_snippet: Optional[str]
    github_url: Optional[str]
    comments: list[CommentResponse] = []
    questions: list[QuestionResponse] = []


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    comment_id: Optional[uuid.UUID] = None


# Відповідь на питання: збережений запис, поле answer лишається сумісним зі старим форматом
class AskResponse(QuestionResponse):
    pass
