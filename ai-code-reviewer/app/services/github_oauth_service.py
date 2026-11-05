"""Вхід і реєстрація через GitHub (OAuth Authorization Code).

Довіряємо лише адресі, яку GitHub позначив як primary і verified. Токен GitHub використовується одразу
для читання профілю й не зберігається.
"""
import logging
import secrets
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.user import User

logger = logging.getLogger(__name__)

AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
TOKEN_URL = "https://github.com/login/oauth/access_token"
USER_URL = "https://api.github.com/user"
EMAILS_URL = "https://api.github.com/user/emails"
TIMEOUT = 10.0


class GithubAuthError(Exception):
    """Помилка входу через GitHub; code потрапляє в адресу повернення, тож це короткий безпечний токен."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass
class GithubIdentity:
    github_id: str
    email: str


def is_configured() -> bool:
    return bool(settings.GITHUB_CLIENT_ID and settings.GITHUB_CLIENT_SECRET)


def callback_url() -> str:
    # Проходить через /api клієнта (nginx або Vite), тож ця адреса має збігатися з Callback URL в налаштуваннях GitHub
    return f"{settings.APP_URL.rstrip('/')}/api/auth/github/callback"


def new_state() -> str:
    return secrets.token_urlsafe(24)


def authorize_url(state: str) -> str:
    query = urlencode(
        {
            "client_id": settings.GITHUB_CLIENT_ID,
            "redirect_uri": callback_url(),
            "scope": "read:user user:email",
            "state": state,
        }
    )
    return f"{AUTHORIZE_URL}?{query}"


async def fetch_identity(code: str) -> GithubIdentity:
    """Обмінює code на токен і читає профіль. Будь-яка помилка перетворюється на GithubAuthError."""
    headers = {"Accept": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as http:
            token_resp = await http.post(
                TOKEN_URL,
                headers=headers,
                data={
                    "client_id": settings.GITHUB_CLIENT_ID,
                    "client_secret": settings.GITHUB_CLIENT_SECRET,
                    "code": code,
                    "redirect_uri": callback_url(),
                },
            )
            token = token_resp.json().get("access_token") if token_resp.status_code == 200 else None
            if not token:
                raise GithubAuthError("token")

            auth = {**headers, "Authorization": f"Bearer {token}", "X-GitHub-Api-Version": "2022-11-28"}
            user_resp = await http.get(USER_URL, headers=auth)
            emails_resp = await http.get(EMAILS_URL, headers=auth)
    except GithubAuthError:
        raise
    except (httpx.HTTPError, ValueError):
        logger.warning("Не вдалося зв'язатися з GitHub", exc_info=True)
        raise GithubAuthError("network")

    if user_resp.status_code != 200 or emails_resp.status_code != 200:
        raise GithubAuthError("profile")

    github_id = str(user_resp.json().get("id") or "")
    emails = [e for e in emails_resp.json() if isinstance(e, dict) and e.get("verified") and e.get("email")]
    if not github_id or not emails:
        raise GithubAuthError("no_email")
    chosen = next((e for e in emails if e.get("primary")), emails[0])
    return GithubIdentity(github_id=github_id, email=chosen["email"].strip().lower())


async def sign_in(db: AsyncSession, identity: GithubIdentity) -> User:
    """Повертає користувача для цього GitHub-акаунта: наявного, зв'язаного за підтвердженою поштою, або нового."""
    result = await db.execute(select(User).where(User.github_id == identity.github_id))
    user = result.scalar_one_or_none()

    if user is None:
        result = await db.execute(select(User).where(User.email == identity.email))
        user = result.scalar_one_or_none()
        if user is not None:
            if not user.email_verified:
                # Хтось міг зареєструвати цю адресу зі своїм паролем, не підтвердивши її. Власник щойно довів,
                # що адреса його, тож пароль скидається, інакше той, хто її зайняв, лишився б з доступом.
                user.hashed_password = None
            user.github_id = identity.github_id
            user.email_verified = True
        else:
            user = User(
                email=identity.email, hashed_password=None, github_id=identity.github_id, email_verified=True, is_active=True
            )
            db.add(user)

    if not user.is_active:
        raise GithubAuthError("inactive")
    await db.commit()
    await db.refresh(user)
    return user
