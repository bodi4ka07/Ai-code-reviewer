import hashlib
import secrets
from datetime import datetime, timedelta
from urllib.parse import quote

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import get_password_hash
from app.models.password_reset import PasswordResetToken
from app.models.user import User

RESEND_SECONDS = 60  # не створюємо новий токен частіше, ніж раз на хвилину


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def create_reset_link(db: AsyncSession, email: str) -> tuple[str, str] | None:
    """Створює одноразове посилання для скидання пароля.

    Повертає (email, посилання) або None, якщо користувача немає, він неактивний
    або посилання щойно вже створювалось. Виклик не повинен давати зрозуміти це користувачу.
    """
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        return None

    now = datetime.utcnow()
    recent = await db.execute(
        select(PasswordResetToken.id).where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.created_at > now - timedelta(seconds=RESEND_SECONDS),
        )
    )
    if recent.first():
        return None

    # Попередні невикористані посилання перестають діяти
    await db.execute(
        update(PasswordResetToken)
        .where(PasswordResetToken.user_id == user.id, PasswordResetToken.used_at.is_(None))
        .values(used_at=now)
    )

    token = secrets.token_urlsafe(32)
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=hash_token(token),
            expires_at=now + timedelta(minutes=settings.PASSWORD_RESET_MINUTES),
        )
    )
    await db.commit()
    return user.email, f"{settings.APP_URL.rstrip('/')}/reset-password?token={quote(token)}"


async def reset_password(db: AsyncSession, token: str, new_password: str) -> None:
    now = datetime.utcnow()
    result = await db.execute(select(PasswordResetToken).where(PasswordResetToken.token_hash == hash_token(token)))
    record = result.scalar_one_or_none()
    if not record or record.used_at is not None or record.expires_at < now:
        raise HTTPException(status_code=400, detail="Посилання недійсне або прострочене")

    user = await db.get(User, record.user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=400, detail="Посилання недійсне або прострочене")

    user.hashed_password = get_password_hash(new_password)
    user.email_verified = True  # лист із посиланням дійшов до власника скриньки
    record.used_at = now
    await db.commit()
