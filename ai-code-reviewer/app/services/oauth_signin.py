"""Спільна для GitHub і Google логіка: знайти або створити користувача за підтвердженою поштою провайдера."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class OAuthError(Exception):
    """Помилка входу через зовнішнього провайдера; code потрапляє в адресу повернення, тож це короткий безпечний токен."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


async def sign_in(db: AsyncSession, id_field: str, provider_id: str, email: str) -> User:
    """Повертає користувача для цього акаунта провайдера: наявного, зв'язаного за підтвердженою поштою, або нового.

    id_field це колонка User з ідентифікатором провайдера (github_id або google_id).
    Пошта вже підтверджена провайдером, тож викликати цю функцію можна лише для таких адрес."""
    column = getattr(User, id_field)
    result = await db.execute(select(User).where(column == provider_id))
    user = result.scalar_one_or_none()

    if user is None:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user is not None:
            if not user.email_verified:
                # Хтось міг зареєструвати цю адресу зі своїм паролем, не підтвердивши її. Власник щойно довів,
                # що адреса його, тож пароль скидається, інакше той, хто її зайняв, лишився б з доступом.
                user.hashed_password = None
            setattr(user, id_field, provider_id)
            user.email_verified = True
        else:
            user = User(email=email, hashed_password=None, email_verified=True, is_active=True, **{id_field: provider_id})
            db.add(user)

    if not user.is_active:
        raise OAuthError("inactive")
    await db.commit()
    await db.refresh(user)
    return user
