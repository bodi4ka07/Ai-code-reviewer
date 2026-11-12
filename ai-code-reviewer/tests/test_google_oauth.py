import pytest
from sqlalchemy import select

from app.models.user import User
from app.services import google_oauth_service as gg
from app.services.google_oauth_service import GoogleAuthError, GoogleIdentity


@pytest.fixture
def configured(monkeypatch):
    monkeypatch.setattr(gg.settings, "GOOGLE_CLIENT_ID", "gid")
    monkeypatch.setattr(gg.settings, "GOOGLE_CLIENT_SECRET", "gsecret")


def fake_identity(monkeypatch, identity=None, error=None):
    async def fetch(code):
        if error:
            raise GoogleAuthError(error)
        return identity

    monkeypatch.setattr(gg, "fetch_identity", fetch)


async def start(client):
    resp = await client.get("/auth/google/login")
    assert resp.status_code == 303
    return resp.cookies["google_oauth_state"], resp.headers["location"]


async def users(session_factory):
    async with session_factory() as db:
        return list((await db.execute(select(User))).scalars().all())


async def test_providers_include_google(client, configured):
    assert (await client.get("/auth/providers")).json()["google"] is True


async def test_not_configured(client):
    assert (await client.get("/auth/providers")).json()["google"] is False
    assert (await client.get("/auth/google/login")).status_code == 503


async def test_login_redirects_to_google_with_state(client, configured):
    state, location = await start(client)
    assert location.startswith("https://accounts.google.com/o/oauth2/v2/auth?")
    assert f"state={state}" in location and "client_id=gid" in location and "response_type=code" in location
    assert "gsecret" not in location
    assert "localhost%3A5173%2Fapi%2Fauth%2Fgoogle%2Fcallback" in location


async def test_callback_creates_verified_account_and_returns_token(client, configured, session_factory, monkeypatch):
    fake_identity(monkeypatch, GoogleIdentity("g-1", "new@example.com"))
    state, _ = await start(client)

    resp = await client.get("/auth/google/callback", params={"code": "abc", "state": state})
    location = resp.headers["location"]
    assert location.startswith("http://localhost:5173/auth/google#token=")
    assert "?" not in location.split("#")[0]  # токен лише у фрагменті

    token = location.split("#token=")[1]
    me = await client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert me.json()["email"] == "new@example.com" and me.json()["email_verified"] is True

    (user,) = await users(session_factory)
    assert user.google_id == "g-1" and user.hashed_password is None and user.github_id is None


async def test_rejects_wrong_or_missing_state(client, configured, monkeypatch):
    fake_identity(monkeypatch, GoogleIdentity("g-1", "new@example.com"))
    await start(client)
    bad = await client.get("/auth/google/callback", params={"code": "abc", "state": "forged"})
    assert bad.headers["location"].endswith("/login?google_error=state")

    client.cookies.clear()
    missing = await client.get("/auth/google/callback", params={"code": "abc", "state": "x"})
    assert missing.headers["location"].endswith("/login?google_error=state")


async def test_user_denied_access(client, configured):
    resp = await client.get("/auth/google/callback", params={"error": "access_denied"})
    assert resp.headers["location"].endswith("/login?google_error=denied")


async def test_reports_errors_without_details(client, configured, monkeypatch):
    fake_identity(monkeypatch, error="unverified")
    state, _ = await start(client)
    resp = await client.get("/auth/google/callback", params={"code": "abc", "state": state})
    assert resp.headers["location"].endswith("/login?google_error=unverified")


async def test_links_existing_verified_password_account(client, configured, session_factory, monkeypatch):
    await client.post("/auth/register", json={"email": "me@example.com", "password": "password123"})
    fake_identity(monkeypatch, GoogleIdentity("g-7", "me@example.com"))
    state, _ = await start(client)
    await client.get("/auth/google/callback", params={"code": "abc", "state": state})

    (user,) = await users(session_factory)
    assert user.google_id == "g-7" and user.hashed_password is not None
    assert (await client.post("/auth/login", data={"username": "me@example.com", "password": "password123"})).status_code == 200


async def test_linking_unverified_account_drops_squatters_password(client, configured, session_factory, monkeypatch):
    async with session_factory() as db:
        db.add(User(email="victim@example.com", hashed_password="x", email_verified=False))
        await db.commit()
    fake_identity(monkeypatch, GoogleIdentity("g-9", "victim@example.com"))
    state, _ = await start(client)
    await client.get("/auth/google/callback", params={"code": "abc", "state": state})

    (user,) = await users(session_factory)
    assert user.google_id == "g-9" and user.email_verified is True and user.hashed_password is None


async def test_google_and_github_link_to_one_account_by_email(client, configured, session_factory, monkeypatch):
    fake_identity(monkeypatch, GoogleIdentity("g-1", "same@example.com"))
    state, _ = await start(client)
    await client.get("/auth/google/callback", params={"code": "abc", "state": state})

    from app.services import github_oauth_service as gh

    monkeypatch.setattr(gh.settings, "GITHUB_CLIENT_ID", "cid")
    monkeypatch.setattr(gh.settings, "GITHUB_CLIENT_SECRET", "secret")

    async def gh_fetch(code):
        return gh.GithubIdentity("42", "same@example.com")

    monkeypatch.setattr(gh, "fetch_identity", gh_fetch)
    resp = await client.get("/auth/github/login")
    gh_state = resp.cookies["gh_oauth_state"]
    await client.get("/auth/github/callback", params={"code": "abc", "state": gh_state})

    (user,) = await users(session_factory)  # один акаунт з обома провайдерами
    assert user.google_id == "g-1" and user.github_id == "42"


async def test_fetch_identity_requires_verified_email(monkeypatch, configured):
    class Resp:
        def __init__(self, payload):
            self.status_code, self._payload = 200, payload

        def json(self):
            return self._payload

    class FakeHttp:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, **k):
            return Resp({"access_token": "ya29.x"})

        async def get(self, url, **k):
            return Resp({"sub": "5", "email": "A@B.c", "email_verified": False})

    monkeypatch.setattr(gg.httpx, "AsyncClient", FakeHttp)
    with pytest.raises(GoogleAuthError) as exc:
        await gg.fetch_identity("code")
    assert exc.value.code == "unverified"


async def test_fetch_identity_parses_profile(monkeypatch, configured):
    class Resp:
        def __init__(self, payload):
            self.status_code, self._payload = 200, payload

        def json(self):
            return self._payload

    class FakeHttp:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, **k):
            return Resp({"access_token": "ya29.x"})

        async def get(self, url, **k):
            return Resp({"sub": "5", "email": "Main@Example.com", "email_verified": True})

    monkeypatch.setattr(gg.httpx, "AsyncClient", FakeHttp)
    assert await gg.fetch_identity("code") == GoogleIdentity("5", "main@example.com")
