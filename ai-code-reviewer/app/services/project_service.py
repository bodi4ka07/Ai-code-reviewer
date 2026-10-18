import uuid

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comment import ReviewComment
from app.models.project import Project
from app.models.review import Review, ReviewStatus
from app.schemas.project import CategoryCount, ProjectStats, ScorePoint

HISTORY_LIMIT = 30


async def get_owned_project(db: AsyncSession, project_id: uuid.UUID, user_id: uuid.UUID) -> Project:
    """Повертає проєкт користувача або 404 (чужий проєкт неможливо відрізнити від неіснуючого)."""
    result = await db.execute(select(Project).where(Project.id == project_id, Project.user_id == user_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Проект не знайдено")
    return project


async def compute_stats(db: AsyncSession, project_id: uuid.UUID) -> ProjectStats:
    total = await db.scalar(select(func.count(Review.id)).where(Review.project_id == project_id))

    done = (Review.project_id == project_id, Review.status == ReviewStatus.DONE)
    completed, avg, low, high = (
        await db.execute(
            select(
                func.count(Review.id),
                func.avg(Review.overall_score),
                func.min(Review.overall_score),
                func.max(Review.overall_score),
            ).where(*done)
        )
    ).one()

    category_rows = await db.execute(
        select(ReviewComment.category, func.count(ReviewComment.id))
        .join(Review, ReviewComment.review_id == Review.id)
        .where(Review.project_id == project_id)
        .group_by(ReviewComment.category)
    )
    categories = [CategoryCount(category=c.value, count=n) for c, n in category_rows.all()]

    # Останні HISTORY_LIMIT завершених рев'ю, у хронологічному порядку для графіка
    history_rows = await db.execute(
        select(Review.id, Review.overall_score, Review.completed_at)
        .where(*done, Review.completed_at.is_not(None))
        .order_by(Review.completed_at.desc())
        .limit(HISTORY_LIMIT)
    )
    history = [ScorePoint(review_id=i, score=s, date=d) for i, s, d in reversed(history_rows.all())]

    return ProjectStats(
        total_reviews=total or 0,
        completed_reviews=completed or 0,
        average_score=round(float(avg), 1) if avg is not None else None,
        min_score=low,
        max_score=high,
        categories=categories,
        score_history=history,
    )
