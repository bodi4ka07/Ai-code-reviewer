from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.project import Project
from app.models.review import Review, ReviewStatus
from app.models.comment import ReviewComment, CommentCategory
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse
from pydantic import BaseModel
from typing import Optional
import uuid

router = APIRouter()


@router.post("/", response_model=ProjectResponse, status_code=201)
async def create_project(
    data: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = Project(**data.model_dump(), user_id=current_user.id)
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


@router.get("/", response_model=list[ProjectResponse])
async def list_projects(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Project).where(Project.user_id == current_user.id))
    return result.scalars().all()


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Проект не знайдено")
    return project


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Проект не знайдено")
    await db.delete(project)
    await db.commit()


class CategoryStats(BaseModel):
    category: str
    count: int


class ProjectStats(BaseModel):
    total_reviews: int
    completed_reviews: int
    average_score: Optional[float]
    min_score: Optional[int]
    max_score: Optional[int]
    bugs_count: int
    security_count: int
    style_count: int
    performance_count: int


@router.get("/{project_id}/stats", response_model=ProjectStats)
async def get_project_stats(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Статистика по проекту — кількість рев'ю, середня оцінка, категорії проблем."""
    # Перевіряємо що проект існує і належить користувачу
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == current_user.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Проект не знайдено")

    # Загальна кількість рев'ю
    total = await db.execute(
        select(func.count(Review.id)).where(Review.project_id == project_id)
    )
    total_reviews = total.scalar() or 0

    # Завершені рев'ю
    completed = await db.execute(
        select(func.count(Review.id)).where(
            Review.project_id == project_id,
            Review.status == ReviewStatus.DONE
        )
    )
    completed_reviews = completed.scalar() or 0

    # Середня, мін, макс оцінка
    scores = await db.execute(
        select(
            func.avg(Review.overall_score),
            func.min(Review.overall_score),
            func.max(Review.overall_score),
        ).where(
            Review.project_id == project_id,
            Review.status == ReviewStatus.DONE
        )
    )
    avg_score, min_score, max_score = scores.one()

    # Підрахунок коментарів по категоріях
    async def count_category(category: CommentCategory) -> int:
        result = await db.execute(
            select(func.count(ReviewComment.id))
            .join(Review, ReviewComment.review_id == Review.id)
            .where(
                Review.project_id == project_id,
                ReviewComment.category == category,
            )
        )
        return result.scalar() or 0

    bugs = await count_category(CommentCategory.BUG)
    security = await count_category(CommentCategory.SECURITY)
    style = await count_category(CommentCategory.STYLE)
    performance = await count_category(CommentCategory.PERFORMANCE)

    return ProjectStats(
        total_reviews=total_reviews,
        completed_reviews=completed_reviews,
        average_score=round(float(avg_score), 1) if avg_score else None,
        min_score=min_score,
        max_score=max_score,
        bugs_count=bugs,
        security_count=security,
        style_count=style,
        performance_count=performance,
    )