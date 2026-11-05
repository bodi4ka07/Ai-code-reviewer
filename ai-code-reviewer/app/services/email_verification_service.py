import secrets
from datetime import datetime, timedelta
from urllib.parse import quote

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.email_verification import EmailVerificationToken
from app.models.user import User
from app.services.password_reset_service import RESEND_SECONDS, hash_token


async def create_verification_link(db: AsyncSession, user: User) -> str | None:
    """Створює одноразове посилання для підтвердження email.

    Повертає None, якщо попереднє посилання створювалось щойно (захист від спаму листами).
    """
    now = datetime.utcnow()
    recent = await db.execute(
        select(EmailVerificationToken.id).where(
            EmailVerificationToken.user_id == user.id,
            EmailVerificationToken.created_at > now - timedelta(seconds=RESEND_SECONDS),
        )
    )
    if recent.first():
        return None

    # Попередні невикористані посилання перестають діяти
    await db.execute(
        update(EmailVerificationToken)
        .where(EmailVerificationToken.user_id == user.id, EmailVerificationToken.used_at.is_(None))
        .values(used_at=now)
    )

    token = secrets.token_urlsafe(32)
    db.add(
        EmailVerificationToken(
            user_id=user.id,
            token_hash=hash_token(token),
            expires_at=now + timedelta(hours=settings.VERIFY_EMAIL_HOURS),
        )
    )
    await db.commit()
    return f"{settings.APP_URL.rstrip('/')}/verify-email?token={quote(token)}"


async def verify_email(db: AsyncSession, token: str) -> None:
    now = datetime.utcnow()
    result = await db.execute(
        select(EmailVerificationToken).where(EmailVerificationToken.token_hash == hash_token(token))
    )
    record = result.scalar_one_or_none()
    if not record or record.used_at is not None or record.expires_at < now:
        raise HTTPException(status_code=400, detail="Посилання недійсне або прострочене")

    user = await db.get(User, record.user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=400, detail="Посилання недійсне або прострочене")

    user.email_verified = True
    record.used_at = now
    await db.commit()
