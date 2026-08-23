from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.project import Project
from app.models.review import Review
from app.models.comment import ReviewComment
from app.schemas.review import ReviewCreate, ReviewResponse, ReviewDetailResponse
from app.tasks import process_review_task
from pydantic import BaseModel
from typing import Optional
import uuid

router = APIRouter()


@router.post("/", response_model=ReviewResponse, status_code=202)
async def create_review(
    data: ReviewCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Project).where(Project.id == data.project_id, Project.user_id == current_user.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Проект не знайдено")

    review = Review(
        project_id=data.project_id,
        code_snippet=data.code_snippet,
        github_url=data.github_url,
    )
    db.add(review)
    await db.commit()
    await db.refresh(review)

    process_review_task.delay(str(review.id))
    return review


@router.get("/{review_id}", response_model=ReviewDetailResponse)
async def get_review(
    review_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Review)
        .options(selectinload(Review.comments), selectinload(Review.project))
        .where(Review.id == review_id)
    )
    review = result.scalar_one_or_none()

    if not review or review.project.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Рев'ю не знайдено")

    return review


class AskRequest(BaseModel):
    question: str
    comment_id: Optional[uuid.UUID] = None


class AskResponse(BaseModel):
    answer: str


@router.post("/{review_id}/ask", response_model=AskResponse)
async def ask_about_review(
    review_id: uuid.UUID,
    data: AskRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Задати уточнююче питання по рев'ю до AI."""
    result = await db.execute(
        select(Review)
        .options(selectinload(Review.comments), selectinload(Review.project))
        .where(Review.id == review_id)
    )
    review = result.scalar_one_or_none()

    if not review or review.project.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Рев'ю не знайдено")

    if review.status != "done":
        raise HTTPException(status_code=400, detail="Рев'ю ще не завершено")

    # Формуємо контекст для AI
    comments_text = "\n".join([
        f"- [{c.category}/{c.severity}] рядок {c.line_number}: {c.message}"
        for c in review.comments
    ])

    prompt = f"""Ти — senior розробник. Користувач має питання по результатах code review.

КОД:
{review.code_snippet or review.github_url}

РЕЗУЛЬТАТИ РЕВ'Ю (score: {review.overall_score}/100):
{review.summary}

КОМЕНТАРІ:
{comments_text}

ПИТАННЯ КОРИСТУВАЧА:
{data.question}

Дай чітку і корисну відповідь на питання. Відповідай українською мовою."""

    from google import genai
    from app.core.config import settings

    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )

    return {"answer": response.text}