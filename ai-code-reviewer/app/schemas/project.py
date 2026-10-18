import uuid
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from app.core.languages import normalize_language


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=1000)
    language: str = "python"

    @field_validator("language")
    @classmethod
    def check_language(cls, v: str) -> str:
        return normalize_language(v)


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=1000)
    language: Optional[str] = None

    @field_validator("language")
    @classmethod
    def check_language(cls, v: Optional[str]) -> Optional[str]:
        return normalize_language(v) if v is not None else None


class ProjectResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str]
    language: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ScorePoint(BaseModel):
    review_id: uuid.UUID
    score: int
    date: datetime


class CategoryCount(BaseModel):
    category: str
    count: int


class ProjectStats(BaseModel):
    total_reviews: int
    completed_reviews: int
    average_score: Optional[float]
    min_score: Optional[int]
    max_score: Optional[int]
    categories: list[CategoryCount]
    score_history: list[ScorePoint]
