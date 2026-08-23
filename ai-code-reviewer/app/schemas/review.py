import uuid
from datetime import datetime
from pydantic import BaseModel, HttpUrl, model_validator
from typing import Optional
from app.models.review import ReviewStatus
from app.schemas.comment import CommentResponse


class ReviewCreate(BaseModel):
    project_id: uuid.UUID
    code_snippet: Optional[str] = None
    github_url: Optional[str] = None

    @model_validator(mode="after")
    def check_source_provided(self):
        if not self.code_snippet and not self.github_url:
            raise ValueError("Потрібно надати або code_snippet або github_url")
        return self


class ReviewResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    status: ReviewStatus
    overall_score: Optional[int]
    summary: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]

    model_config = {"from_attributes": True}


class ReviewDetailResponse(ReviewResponse):
    comments: list[CommentResponse] = []
