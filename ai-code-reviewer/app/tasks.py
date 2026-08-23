from app.worker import celery_app


@celery_app.task(name="process_review")
def process_review_task(review_id: str):
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_process_review(review_id))
    finally:
        loop.close()


async def _process_review(review_id: str):
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    from app.core.config import settings
    from app.models.user import User  # noqa
    from app.models.project import Project  # noqa
    from app.models.review import Review, ReviewStatus
    from app.models.comment import ReviewComment, CommentCategory, CommentSeverity
    from app.agent.agent import CodeReviewAgent
    from sqlalchemy import select
    from datetime import datetime

    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with SessionLocal() as db:
        try:
            result = await db.execute(select(Review).where(Review.id == review_id))
            review = result.scalar_one_or_none()

            if not review:
                return

            review.status = ReviewStatus.PROCESSING
            await db.commit()

            try:
                agent = CodeReviewAgent()
                # Передаємо db для RAG пошуку
                analysis = await agent.analyze(
                    code=review.code_snippet,
                    github_url=review.github_url,
                    db=db,
                )

                review.overall_score = analysis.overall_score
                review.summary = analysis.summary
                review.status = ReviewStatus.DONE
                review.completed_at = datetime.utcnow()

                for comment in analysis.comments:
                    db_comment = ReviewComment(
                        review_id=review.id,
                        category=CommentCategory(comment.category),
                        severity=CommentSeverity(comment.severity),
                        line_number=comment.line_number,
                        message=comment.message,
                        suggestion=comment.suggestion,
                    )
                    db.add(db_comment)

                await db.commit()

            except Exception as e:
                review.status = ReviewStatus.FAILED
                review.summary = f"Помилка аналізу: {str(e)}"
                await db.commit()
        finally:
            await engine.dispose()
            