async def test_register_and_login(client):
    resp = await client.post("/auth/register", json={"email": "a@example.com", "password": "password123"})
    assert resp.status_code == 201
    assert "hashed_password" not in resp.json()

    resp = await client.post("/auth/login", data={"username": "a@example.com", "password": "password123"})
    assert resp.status_code == 200
    assert resp.json()["token_type"] == "bearer"


async def test_register_duplicate_email(client):
    body = {"email": "a@example.com", "password": "password123"}
    await client.post("/auth/register", json=body)
    resp = await client.post("/auth/register", json=body)
    assert resp.status_code == 400


async def test_register_rejects_short_password(client):
    resp = await client.post("/auth/register", json={"email": "a@example.com", "password": "short"})
    assert resp.status_code == 422


async def test_login_wrong_password(client):
    await client.post("/auth/register", json={"email": "a@example.com", "password": "password123"})
    resp = await client.post("/auth/login", data={"username": "a@example.com", "password": "wrong-password"})
    assert resp.status_code == 401


async def test_me_requires_token(client):
    assert (await client.get("/users/me")).status_code == 401
    assert (await client.get("/users/me", headers={"Authorization": "Bearer garbage"})).status_code == 401


async def test_me_returns_profile(client, auth):
    resp = await client.get("/users/me", headers=auth)
    assert resp.status_code == 200
    assert resp.json()["email"] == "user@example.com"
