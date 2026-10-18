import os

# Змінні середовища мають бути встановлені до імпорту застосунку
os.environ.update(
    DATABASE_URL="sqlite+aiosqlite://",
    SECRET_KEY="test-secret-key",
    GEMINI_API_KEY="test-gemini-key",
    DEBUG="false",
)

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import comment, project, review, user  # noqa: E402,F401


@pytest_asyncio.fixture
async def session_factory():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    await engine.dispose()


@pytest.fixture
def queued(monkeypatch):
    """Підміняє Celery: зберігає id рев'ю, які були поставлені в чергу."""
    ids: list[str] = []
    monkeypatch.setattr("app.api.routes.reviews.process_review_task.delay", lambda rid: ids.append(rid))
    return ids


@pytest_asyncio.fixture
async def client(session_factory, queued):
    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


async def register_and_login(client: AsyncClient, email: str = "user@example.com", password: str = "password123") -> dict:
    await client.post("/auth/register", json={"email": email, "password": password})
    resp = await client.post("/auth/login", data={"username": email, "password": password})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest_asyncio.fixture
async def auth(client):
    return await register_and_login(client)


@pytest_asyncio.fixture
async def other_auth(client):
    return await register_and_login(client, "other@example.com")


@pytest_asyncio.fixture
async def project_id(client, auth):
    resp = await client.post("/projects/", json={"name": "demo", "language": "python"}, headers=auth)
    return resp.json()["id"]
