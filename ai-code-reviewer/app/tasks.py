import asyncio
import logging
import uuid
from datetime import datetime

from app.worker import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="process_review")
def process_review_task(review_id: str):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_process_review(review_id))
    finally:
        loop.close()


async def _process_review(review_id: str, session_factory=None):
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from app.agent.agent import AgentError, CodeReviewAgent
    from app.core.config import settings
    from app.models.comment import CommentCategory, CommentSeverity, ReviewComment
    from app.models.project import Project  # noqa: F401
    from app.models.review import Review, ReviewStatus
    from app.models.user import User  # noqa: F401

    engine = None
    if session_factory is None:
        engine = create_async_engine(settings.DATABASE_URL, echo=False)
        session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with session_factory() as db:
            result = await db.execute(select(Review).where(Review.id == uuid.UUID(review_id)))
            review = result.scalar_one_or_none()
            if not review:
                return

            review.status = ReviewStatus.PROCESSING
            await db.commit()

            try:
                analysis = await CodeReviewAgent().analyze(
                    code=review.code_snippet,
                    github_url=review.github_url,
                    language=review.language,
                    db=db,
                )

                review.overall_score = analysis.overall_score
                review.summary = analysis.summary
                if not review.code_snippet:
                    review.code_snippet = analysis.code  # зберігаємо код, завантажений з GitHub
                review.status = ReviewStatus.DONE
                review.completed_at = datetime.utcnow()

                for c in analysis.comments:
                    db.add(
                        ReviewComment(
                            review_id=review.id,
                            category=CommentCategory(c.category),
                            severity=CommentSeverity(c.severity),
                            line_number=c.line_number,
                            message=c.message,
                            suggestion=c.suggestion,
                            reference=c.reference[:255] if c.reference else None,
                        )
                    )
                await db.commit()

            except (AgentError, ValueError) as e:
                # Повідомлення цих винятків написані для користувача
                await db.rollback()
                review.status = ReviewStatus.FAILED
                review.error_message = str(e)
                await db.commit()
            except Exception:
                logger.exception("Помилка під час обробки рев'ю %s", review_id)
                await db.rollback()
                review.status = ReviewStatus.FAILED
                review.error_message = "Внутрішня помилка аналізу. Спробуйте ще раз."
                await db.commit()
    finally:
        if engine is not None:
            await engine.dispose()
