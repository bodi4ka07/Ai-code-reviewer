import logging
from datetime import datetime, timedelta

import pytest
from sqlalchemy import select

from app.models.password_reset import PasswordResetToken
from app.services import email_service, password_reset_service

EMAIL = "user@example.com"  # користувач з фікстури auth


@pytest.fixture
def sent(monkeypatch):
    """Перехоплює листи: список (email, посилання)."""
    mails: list[tuple[str, str]] = []
    monkeypatch.setattr(email_service, "send_password_reset_email", lambda to, link: mails.append((to, link)))
    return mails


def token_from(link: str) -> str:
    return link.split("token=")[1]


async def request_reset(client, email=EMAIL):
    return await client.post("/auth/forgot-password", json={"email": email})


async def test_full_reset_flow(client, auth, sent):
    resp = await request_reset(client)
    assert resp.status_code == 200
    assert len(sent) == 1
    to, link = sent[0]
    assert to == EMAIL
    assert link.startswith("http://localhost:5173/reset-password?token=")

    reset = await client.post("/auth/reset-password", json={"token": token_from(link), "password": "brand-new-pass"})
    assert reset.status_code == 200

    old = await client.post("/auth/login", data={"username": EMAIL, "password": "password123"})
    new = await client.post("/auth/login", data={"username": EMAIL, "password": "brand-new-pass"})
    assert old.status_code == 401
    assert new.status_code == 200


async def test_response_does_not_reveal_whether_account_exists(client, auth, sent):
    known = await request_reset(client)
    unknown = await request_reset(client, "nobody@example.com")
    assert known.status_code == unknown.status_code == 200
    assert known.json() == unknown.json()
    assert len(sent) == 1  # лист лише для існуючого акаунта


async def test_token_is_single_use(client, auth, sent):
    await request_reset(client)
    token = token_from(sent[0][1])
    first = await client.post("/auth/reset-password", json={"token": token, "password": "first-new-pass"})
    second = await client.post("/auth/reset-password", json={"token": token, "password": "second-new-pass"})
    assert first.status_code == 200
    assert second.status_code == 400
    assert (await client.post("/auth/login", data={"username": EMAIL, "password": "first-new-pass"})).status_code == 200


async def test_expired_token_is_rejected(client, auth, sent, session_factory):
    await request_reset(client)
    token = token_from(sent[0][1])
    async with session_factory() as db:
        record = (await db.execute(select(PasswordResetToken))).scalar_one()
        record.expires_at = datetime.utcnow() - timedelta(minutes=1)
        await db.commit()

    resp = await client.post("/auth/reset-password", json={"token": token, "password": "brand-new-pass"})
    assert resp.status_code == 400
    assert (await client.post("/auth/login", data={"username": EMAIL, "password": "password123"})).status_code == 200


async def test_garbage_token_is_rejected(client, auth):
    resp = await client.post("/auth/reset-password", json={"token": "x" * 40, "password": "brand-new-pass"})
    assert resp.status_code == 400


async def test_new_password_must_be_strong_enough(client, auth, sent):
    await request_reset(client)
    resp = await client.post("/auth/reset-password", json={"token": token_from(sent[0][1]), "password": "short"})
    assert resp.status_code == 422


async def test_only_hash_of_token_is_stored(client, auth, sent, session_factory):
    await request_reset(client)
    token = token_from(sent[0][1])
    async with session_factory() as db:
        record = (await db.execute(select(PasswordResetToken))).scalar_one()
    assert record.token_hash != token
    assert record.token_hash == password_reset_service.hash_token(token)


async def test_repeated_requests_are_throttled(client, auth, sent):
    await request_reset(client)
    await request_reset(client)
    assert len(sent) == 1


async def test_newer_link_invalidates_older_one(client, auth, sent, session_factory):
    await request_reset(client)
    async with session_factory() as db:  # відсуваємо створення, щоб пройти ліміт частоти
        record = (await db.execute(select(PasswordResetToken))).scalar_one()
        record.created_at = datetime.utcnow() - timedelta(minutes=5)
        await db.commit()
    await request_reset(client)

    old, new = token_from(sent[0][1]), token_from(sent[1][1])
    assert (await client.post("/auth/reset-password", json={"token": old, "password": "brand-new-pass"})).status_code == 400
    assert (await client.post("/auth/reset-password", json={"token": new, "password": "brand-new-pass"})).status_code == 200


async def test_link_is_logged_when_smtp_is_not_configured(client, auth, caplog):
    with caplog.at_level(logging.WARNING):
        await request_reset(client)
    assert "SMTP не налаштовано" in caplog.text
    assert "reset-password?token=" in caplog.text


def test_email_is_sent_through_smtp_when_configured(monkeypatch):
    monkeypatch.setattr(email_service.settings, "SMTP_HOST", "smtp.gmail.com")
    monkeypatch.setattr(email_service.settings, "SMTP_USER", "me@gmail.com")
    monkeypatch.setattr(email_service.settings, "SMTP_PASSWORD", "app-password")
    captured = {}
    monkeypatch.setattr(email_service, "send_email", lambda to, subject, body: captured.update(to=to, subject=subject, body=body))

    email_service.send_password_reset_email("user@example.com", "http://localhost:5173/reset-password?token=abc")

    assert captured["to"] == "user@example.com"
    assert "http://localhost:5173/reset-password?token=abc" in captured["body"]


def test_smtp_errors_do_not_break_the_request(monkeypatch, caplog):
    monkeypatch.setattr(email_service.settings, "SMTP_HOST", "smtp.gmail.com")
    monkeypatch.setattr(email_service.settings, "SMTP_USER", "me@gmail.com")
    monkeypatch.setattr(email_service.settings, "SMTP_PASSWORD", "app-password")

    def broken(*args):
        raise OSError("connection refused")

    monkeypatch.setattr(email_service, "send_email", broken)
    email_service.send_password_reset_email("user@example.com", "http://x/reset-password?token=abc")  # не кидає виняток
    assert "Не вдалося надіслати лист" in caplog.text


def test_link_is_logged_in_debug_mode_when_smtp_fails(monkeypatch, caplog):
    monkeypatch.setattr(email_service.settings, "SMTP_HOST", "smtp.gmail.com")
    monkeypatch.setattr(email_service.settings, "SMTP_USER", "me@gmail.com")
    monkeypatch.setattr(email_service.settings, "SMTP_PASSWORD", "wrong")
    monkeypatch.setattr(email_service.settings, "DEBUG", True)

    def broken(*args):
        raise OSError("auth failed")

    monkeypatch.setattr(email_service, "send_email", broken)
    email_service.send_password_reset_email("user@example.com", "http://x/reset-password?token=abc")
    assert "http://x/reset-password?token=abc" in caplog.text


def test_link_is_not_logged_outside_debug_mode_when_smtp_fails(monkeypatch, caplog):
    monkeypatch.setattr(email_service.settings, "SMTP_HOST", "smtp.gmail.com")
    monkeypatch.setattr(email_service.settings, "SMTP_USER", "me@gmail.com")
    monkeypatch.setattr(email_service.settings, "SMTP_PASSWORD", "wrong")
    monkeypatch.setattr(email_service.settings, "DEBUG", False)

    def broken(*args):
        raise OSError("auth failed")

    monkeypatch.setattr(email_service, "send_email", broken)
    email_service.send_password_reset_email("user@example.com", "http://x/reset-password?token=abc")
    assert "token=abc" not in caplog.text  # у production токен не потрапляє в журнал
