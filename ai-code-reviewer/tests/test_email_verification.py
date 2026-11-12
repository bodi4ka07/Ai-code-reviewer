from datetime import datetime, timedelta

import pytest
from sqlalchemy import select

from app.models.email_verification import EmailVerificationToken
from app.services import email_service

EMAIL = "new@example.com"
PASSWORD = "password123"


@pytest.fixture
def sent(monkeypatch):
    """Вмикає «налаштовану» пошту й перехоплює листи підтвердження: список (email, посилання)."""
    mails: list[tuple[str, str]] = []
    monkeypatch.setattr(email_service, "smtp_configured", lambda: True)
    monkeypatch.setattr(email_service, "send_verification_email", lambda to, link: mails.append((to, link)))
    monkeypatch.setattr(email_service, "send_password_reset_email", lambda to, link: mails.append((to, link)))
    return mails


def token_from(link: str) -> str:
    return link.split("token=")[1]


async def register(client, email=EMAIL, password=PASSWORD):
    return await client.post("/auth/register", json={"email": email, "password": password})


async def login(client, email=EMAIL, password=PASSWORD):
    return await client.post("/auth/login", data={"username": email, "password": password})


async def test_without_smtp_account_is_active_immediately(client):
    resp = await register(client)
    assert resp.status_code == 201
    assert resp.json()["email_verified"] is True
    assert (await login(client)).status_code == 200


async def test_full_verification_flow(client, sent):
    resp = await register(client)
    assert resp.status_code == 201
    assert resp.json()["email_verified"] is False
    assert len(sent) == 1
    to, link = sent[0]
    assert to == EMAIL
    assert link.startswith("http://localhost:5173/verify-email?token=")

    blocked = await login(client)
    assert blocked.status_code == 403

    verified = await client.post("/auth/verify-email", json={"token": token_from(link)})
    assert verified.status_code == 200
    assert (await login(client)).status_code == 200


async def test_wrong_password_is_not_told_apart_from_unverified(client, sent):
    await register(client)
    resp = await login(client, password="wrong-password")
    assert resp.status_code == 401


async def test_token_is_single_use(client, sent):
    await register(client)
    token = token_from(sent[0][1])
    assert (await client.post("/auth/verify-email", json={"token": token})).status_code == 200
    assert (await client.post("/auth/verify-email", json={"token": token})).status_code == 400


async def test_expired_token_is_rejected(client, sent, session_factory):
    await register(client)
    token = token_from(sent[0][1])
    async with session_factory() as db:
        record = (await db.execute(select(EmailVerificationToken))).scalar_one()
        record.expires_at = datetime.utcnow() - timedelta(minutes=1)
        await db.commit()

    assert (await client.post("/auth/verify-email", json={"token": token})).status_code == 400
    assert (await login(client)).status_code == 403


async def test_garbage_token_is_rejected(client):
    resp = await client.post("/auth/verify-email", json={"token": "x" * 40})
    assert resp.status_code == 400


async def test_resend_is_throttled_and_does_not_reveal_accounts(client, sent):
    await register(client)
    assert len(sent) == 1

    known = await client.post("/auth/resend-verification", json={"email": EMAIL})
    unknown = await client.post("/auth/resend-verification", json={"email": "nobody@example.com"})
    assert known.status_code == unknown.status_code == 200
    assert known.json() == unknown.json()
    assert len(sent) == 1  # щойно вже надсилали, тож повторний лист не створюється


async def test_resend_after_cooldown_invalidates_old_link(client, sent, session_factory):
    await register(client)
    old_token = token_from(sent[0][1])
    async with session_factory() as db:
        record = (await db.execute(select(EmailVerificationToken))).scalar_one()
        record.created_at = datetime.utcnow() - timedelta(minutes=5)
        await db.commit()

    await client.post("/auth/resend-verification", json={"email": EMAIL})
    assert len(sent) == 2
    assert (await client.post("/auth/verify-email", json={"token": old_token})).status_code == 400
    assert (await client.post("/auth/verify-email", json={"token": token_from(sent[1][1])})).status_code == 200


async def test_unverified_registration_can_be_redone(client, sent):
    await register(client, password="first-password")
    again = await register(client, password="second-password")
    assert again.status_code == 201

    await client.post("/auth/verify-email", json={"token": token_from(sent[0][1])})
    assert (await login(client, password="first-password")).status_code == 401
    assert (await login(client, password="second-password")).status_code == 200


async def test_verified_email_cannot_be_registered_again(client, sent):
    await register(client)
    await client.post("/auth/verify-email", json={"token": token_from(sent[0][1])})
    resp = await register(client, password="another-password")
    assert resp.status_code == 400


async def test_password_reset_also_confirms_email(client, sent):
    await register(client)
    assert (await login(client)).status_code == 403

    await client.post("/auth/forgot-password", json={"email": EMAIL})
    assert len(sent) == 2  # лист підтвердження і лист скидання пароля
    reset = await client.post(
        "/auth/reset-password", json={"token": token_from(sent[1][1]), "password": "brand-new-pass"}
    )
    assert reset.status_code == 200
    # лист із посиланням дійшов до власника скриньки, тож email підтверджено
    assert (await login(client, password="brand-new-pass")).status_code == 200
