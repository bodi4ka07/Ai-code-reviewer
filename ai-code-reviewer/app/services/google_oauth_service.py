"""Вхід і реєстрація через Google (OAuth 2.0, Authorization Code).

Довіряємо лише адресі, яку Google позначив як підтверджену. Токен Google використовується одразу
для читання профілю й не зберігається."""
import logging
import secrets
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.user import User
from app.services import oauth_signin
from app.services.oauth_signin import OAuthError

logger = logging.getLogger(__name__)

AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
TIMEOUT = 10.0

GoogleAuthError = OAuthError


@dataclass
class GoogleIdentity:
    google_id: str
    email: str


def is_configured() -> bool:
    return bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)


def callback_url() -> str:
    # Проходить через /api клієнта, тож ця адреса має збігатися з Authorized redirect URI в Google Cloud Console
    return f"{settings.APP_URL.rstrip('/')}/api/auth/google/callback"


def new_state() -> str:
    return secrets.token_urlsafe(24)


def authorize_url(state: str) -> str:
    query = urlencode(
        {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": callback_url(),
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "prompt": "select_account",
        }
    )
    return f"{AUTHORIZE_URL}?{query}"


async def fetch_identity(code: str) -> GoogleIdentity:
    """Обмінює code на токен і читає профіль. Будь-яка помилка перетворюється на GoogleAuthError."""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as http:
            token_resp = await http.post(
                TOKEN_URL,
                data={
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "code": code,
                    "redirect_uri": callback_url(),
                    "grant_type": "authorization_code",
                },
            )
            token = token_resp.json().get("access_token") if token_resp.status_code == 200 else None
            if not token:
                raise GoogleAuthError("token")
            info_resp = await http.get(USERINFO_URL, headers={"Authorization": f"Bearer {token}"})
    except GoogleAuthError:
        raise
    except (httpx.HTTPError, ValueError):
        logger.warning("Не вдалося зв'язатися з Google", exc_info=True)
        raise GoogleAuthError("network")

    if info_resp.status_code != 200:
        raise GoogleAuthError("profile")
    info = info_resp.json()
    google_id = str(info.get("sub") or "")
    email = str(info.get("email") or "").strip().lower()
    if not google_id or not email:
        raise GoogleAuthError("no_email")
    if info.get("email_verified") not in (True, "true"):
        raise GoogleAuthError("unverified")
    return GoogleIdentity(google_id=google_id, email=email)


async def sign_in(db: AsyncSession, identity: GoogleIdentity) -> User:
    return await oauth_signin.sign_in(db, "google_id", identity.google_id, identity.email)
