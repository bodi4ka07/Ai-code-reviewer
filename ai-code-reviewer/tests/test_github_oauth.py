import pytest
from sqlalchemy import select

from app.models.user import User
from app.services import github_oauth_service as gh
from app.services.github_oauth_service import GithubAuthError, GithubIdentity


@pytest.fixture
def configured(monkeypatch):
    monkeypatch.setattr(gh.settings, "GITHUB_CLIENT_ID", "cid")
    monkeypatch.setattr(gh.settings, "GITHUB_CLIENT_SECRET", "secret")


def fake_identity(monkeypatch, identity=None, error=None):
    async def fetch(code):
        if error:
            raise GithubAuthError(error)
        return identity

    monkeypatch.setattr(gh, "fetch_identity", fetch)


async def start(client):
    """Імітує початок входу й повертає state, який GitHub поверне в callback."""
    resp = await client.get("/auth/github/login")
    assert resp.status_code == 303
    return resp.cookies["gh_oauth_state"], resp.headers["location"]


async def users(session_factory):
    async with session_factory() as db:
        return list((await db.execute(select(User))).scalars().all())


async def test_providers_reflect_configuration(client, configured):
    assert (await client.get("/auth/providers")).json() == {"github": True}


async def test_providers_when_not_configured(client):
    assert (await client.get("/auth/providers")).json() == {"github": False}
    assert (await client.get("/auth/github/login")).status_code == 503


async def test_login_redirects_to_github_with_state(client, configured):
    state, location = await start(client)
    assert location.startswith("https://github.com/login/oauth/authorize?")
    assert f"state={state}" in location and "client_id=cid" in location
    assert "secret" not in location  # секрет застосунку ніколи не потрапляє в адресу
    assert "localhost%3A5173%2Fapi%2Fauth%2Fgithub%2Fcallback" in location


async def test_callback_creates_verified_account_and_returns_token(client, configured, session_factory, monkeypatch):
    fake_identity(monkeypatch, GithubIdentity("42", "new@example.com"))
    state, _ = await start(client)

    resp = await client.get("/auth/github/callback", params={"code": "abc", "state": state})
    assert resp.status_code == 303
    location = resp.headers["location"]
    assert location.startswith("http://localhost:5173/auth/github#token=")
    assert "?" not in location.split("#")[0]  # токен лише у фрагменті, не в query

    token = location.split("#token=")[1]
    me = await client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200 and me.json()["email"] == "new@example.com" and me.json()["email_verified"] is True

    (user,) = await users(session_factory)
    assert user.github_id == "42" and user.hashed_password is None


async def test_github_account_cannot_login_with_password(client, configured, monkeypatch):
    fake_identity(monkeypatch, GithubIdentity("42", "new@example.com"))
    state, _ = await start(client)
    await client.get("/auth/github/callback", params={"code": "abc", "state": state})

    resp = await client.post("/auth/login", data={"username": "new@example.com", "password": "password123"})
    assert resp.status_code == 401


async def test_callback_rejects_wrong_or_missing_state(client, configured, monkeypatch):
    fake_identity(monkeypatch, GithubIdentity("42", "new@example.com"))
    await start(client)

    bad = await client.get("/auth/github/callback", params={"code": "abc", "state": "forged"})
    assert bad.headers["location"].endswith("/login?github_error=state")

    client.cookies.clear()
    missing = await client.get("/auth/github/callback", params={"code": "abc", "state": "anything"})
    assert missing.headers["location"].endswith("/login?github_error=state")


async def test_callback_user_denied_access(client, configured):
    resp = await client.get("/auth/github/callback", params={"error": "access_denied"})
    assert resp.headers["location"].endswith("/login?github_error=denied")


async def test_callback_reports_github_errors_without_details(client, configured, monkeypatch):
    fake_identity(monkeypatch, error="no_email")
    state, _ = await start(client)
    resp = await client.get("/auth/github/callback", params={"code": "abc", "state": state})
    assert resp.headers["location"].endswith("/login?github_error=no_email")


async def test_links_existing_verified_password_account(client, configured, session_factory, monkeypatch):
    await client.post("/auth/register", json={"email": "me@example.com", "password": "password123"})
    fake_identity(monkeypatch, GithubIdentity("7", "me@example.com"))
    state, _ = await start(client)
    await client.get("/auth/github/callback", params={"code": "abc", "state": state})

    (user,) = await users(session_factory)  # новий акаунт не створено, лише зв'язано
    assert user.github_id == "7" and user.hashed_password is not None
    assert (await client.post("/auth/login", data={"username": "me@example.com", "password": "password123"})).status_code == 200


async def test_linking_unverified_account_drops_squatters_password(client, configured, session_factory, monkeypatch):
    # Хтось зареєстрував чужу адресу зі своїм паролем і не підтвердив її
    async with session_factory() as db:
        db.add(User(email="victim@example.com", hashed_password="x", email_verified=False))
        await db.commit()

    fake_identity(monkeypatch, GithubIdentity("9", "victim@example.com"))
    state, _ = await start(client)
    await client.get("/auth/github/callback", params={"code": "abc", "state": state})

    (user,) = await users(session_factory)
    assert user.github_id == "9" and user.email_verified is True
    assert user.hashed_password is None  # пароль зловмисника більше не діє


async def test_returning_github_user_is_found_by_github_id(client, configured, session_factory, monkeypatch):
    for _ in range(2):
        fake_identity(monkeypatch, GithubIdentity("42", "new@example.com"))
        state, _ = await start(client)
        resp = await client.get("/auth/github/callback", params={"code": "abc", "state": state})
        assert "#token=" in resp.headers["location"]
    assert len(await users(session_factory)) == 1


async def test_fetch_identity_picks_primary_verified_email(monkeypatch, configured):
    calls = []

    class Resp:
        def __init__(self, status, payload):
            self.status_code, self._payload = status, payload

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
            calls.append(url)
            return Resp(200, {"access_token": "gho_x"})

        async def get(self, url, **k):
            calls.append(url)
            if url.endswith("/user"):
                return Resp(200, {"id": 5})
            return Resp(
                200,
                [
                    {"email": "unverified@example.com", "primary": True, "verified": False},
                    {"email": "Other@Example.com", "primary": False, "verified": True},
                    {"email": "Main@Example.com", "primary": True, "verified": True},
                ],
            )

    monkeypatch.setattr(gh.httpx, "AsyncClient", FakeHttp)
    identity = await gh.fetch_identity("code")
    assert identity == GithubIdentity("5", "main@example.com")


async def test_fetch_identity_needs_a_verified_email(monkeypatch, configured):
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
            return Resp({"access_token": "gho_x"})

        async def get(self, url, **k):
            return Resp({"id": 5}) if url.endswith("/user") else Resp([{"email": "a@b.c", "primary": True, "verified": False}])

    monkeypatch.setattr(gh.httpx, "AsyncClient", FakeHttp)
    with pytest.raises(GithubAuthError) as exc:
        await gh.fetch_identity("code")
    assert exc.value.code == "no_email"
