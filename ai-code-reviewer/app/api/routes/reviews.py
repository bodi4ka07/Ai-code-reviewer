import logging
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.review import ReviewStatus
from app.models.user import User
from app.schemas.review import AskRequest, AskResponse, ReviewCreate, ReviewDetailResponse, ReviewResponse
from app.services import project_service, review_service
from app.tasks import process_review_task

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/", response_model=ReviewResponse, status_code=202)
async def create_review(
    data: ReviewCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = await project_service.get_owned_project(db, data.project_id, current_user.id)
    review = await review_service.create_review(db, data, project)

    try:
        process_review_task.delay(str(review.id))
    except Exception:
        # Черга недоступна: фіксуємо помилку, щоб рев'ю не зависло в "pending"
        logger.exception("Не вдалося поставити рев'ю %s в чергу", review.id)
        review.status = ReviewStatus.FAILED
        review.error_message = "Черга обробки недоступна. Спробуйте пізніше."
        await db.commit()
        await db.refresh(review)
    return review


@router.get("/{review_id}", response_model=ReviewDetailResponse)
async def get_review(
    review_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await review_service.get_owned_review(db, review_id, current_user.id)


@router.post("/{review_id}/ask", response_model=AskResponse)
async def ask_about_review(
    review_id: uuid.UUID,
    data: AskRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Уточнююче питання до AI по рев'ю або по конкретному коментарю."""
    review = await review_service.get_owned_review(db, review_id, current_user.id)
    answer = await review_service.answer_question(review, data.question, data.comment_id)
    return {"answer": answer}
