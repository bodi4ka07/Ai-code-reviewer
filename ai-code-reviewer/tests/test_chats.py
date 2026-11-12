import uuid
from types import SimpleNamespace


class FakeGemini:
    """Підміна Gemini: запам'ятовує, що їй передали, і відповідає по черзі."""

    def __init__(self, *answers):
        self.answers = list(answers) or ["Відповідь AI"]
        self.calls = []
        self.aio = SimpleNamespace(models=SimpleNamespace(generate_content=self._generate))

    async def _generate(self, model, contents, config=None):
        self.calls.append({"contents": contents, "config": config})
        return SimpleNamespace(text=self.answers.pop(0) if len(self.answers) > 1 else self.answers[0])


def use_fake(monkeypatch, fake):
    monkeypatch.setattr("google.genai.Client", lambda api_key: fake)


def texts(contents):
    return [c.parts[0].text for c in contents]


async def test_create_list_and_delete_chat(client, auth):
    first = (await client.post("/chats/", json={}, headers=auth)).json()
    second = (await client.post("/chats/", json={"title": "Мій чат"}, headers=auth)).json()
    assert first["title"] == "Новий чат"
    assert second["title"] == "Мій чат"

    listed = (await client.get("/chats/", headers=auth)).json()
    assert len(listed) == 2

    assert (await client.delete(f"/chats/{first['id']}", headers=auth)).status_code == 204
    assert [c["id"] for c in (await client.get("/chats/", headers=auth)).json()] == [second["id"]]
    assert (await client.get(f"/chats/{first['id']}", headers=auth)).status_code == 404


async def test_send_message_saves_history_and_titles_chat(client, auth, monkeypatch):
    use_fake(monkeypatch, FakeGemini("Це **відповідь**"))
    chat = (await client.post("/chats/", json={}, headers=auth)).json()

    resp = await client.post(f"/chats/{chat['id']}/messages", json={"content": "Що робить eval?"}, headers=auth)
    assert resp.status_code == 200
    body = resp.json()
    assert body["user_message"]["role"] == "user"
    assert body["assistant_message"] == {**body["assistant_message"], "role": "assistant", "content": "Це **відповідь**"}
    assert body["chat"]["title"] == "Що робить eval?"  # назва береться з першого питання

    detail = (await client.get(f"/chats/{chat['id']}", headers=auth)).json()
    assert [m["role"] for m in detail["messages"]] == ["user", "assistant"]


async def test_history_is_sent_to_ai_in_order(client, auth, monkeypatch):
    fake = FakeGemini("відповідь 1", "відповідь 2")
    use_fake(monkeypatch, fake)
    chat = (await client.post("/chats/", json={}, headers=auth)).json()

    await client.post(f"/chats/{chat['id']}/messages", json={"content": "питання 1"}, headers=auth)
    await client.post(f"/chats/{chat['id']}/messages", json={"content": "питання 2"}, headers=auth)

    second_call = fake.calls[1]["contents"]
    assert texts(second_call) == ["питання 1", "відповідь 1", "питання 2"]
    assert [c.role for c in second_call] == ["user", "model", "user"]
    assert fake.calls[1]["config"].system_instruction  # системна інструкція передається


async def test_title_is_not_overwritten_by_later_messages(client, auth, monkeypatch):
    use_fake(monkeypatch, FakeGemini())
    chat = (await client.post("/chats/", json={"title": "Власна назва"}, headers=auth)).json()
    resp = await client.post(f"/chats/{chat['id']}/messages", json={"content": "питання"}, headers=auth)
    assert resp.json()["chat"]["title"] == "Власна назва"


async def test_chats_are_private(client, auth, other_auth, monkeypatch):
    use_fake(monkeypatch, FakeGemini())
    chat = (await client.post("/chats/", json={}, headers=auth)).json()

    assert (await client.get(f"/chats/{chat['id']}", headers=other_auth)).status_code == 404
    assert (await client.delete(f"/chats/{chat['id']}", headers=other_auth)).status_code == 404
    resp = await client.post(f"/chats/{chat['id']}/messages", json={"content": "привіт"}, headers=other_auth)
    assert resp.status_code == 404
    assert (await client.get("/chats/", headers=other_auth)).json() == []
    assert (await client.get(f"/chats/{uuid.uuid4()}", headers=auth)).status_code == 404


async def test_chats_require_auth(client):
    assert (await client.get("/chats/")).status_code == 401
    assert (await client.post("/chats/", json={})).status_code == 401


async def test_message_validation(client, auth):
    chat = (await client.post("/chats/", json={}, headers=auth)).json()
    assert (await client.post(f"/chats/{chat['id']}/messages", json={"content": ""}, headers=auth)).status_code == 422
    too_long = {"content": "x" * 4001}
    assert (await client.post(f"/chats/{chat['id']}/messages", json=too_long, headers=auth)).status_code == 422


async def test_ai_failure_saves_nothing(client, auth, monkeypatch):
    class Broken:
        aio = SimpleNamespace(models=SimpleNamespace(generate_content=None))

    async def boom(model, contents, config=None):
        raise RuntimeError("secret internal detail")

    Broken.aio.models.generate_content = boom
    use_fake(monkeypatch, Broken())
    chat = (await client.post("/chats/", json={}, headers=auth)).json()

    resp = await client.post(f"/chats/{chat['id']}/messages", json={"content": "питання"}, headers=auth)
    assert resp.status_code == 503
    assert "secret" not in resp.text
    assert (await client.get(f"/chats/{chat['id']}", headers=auth)).json()["messages"] == []


async def test_only_recent_history_is_sent(client, auth, monkeypatch):
    from app.services import chat_service

    fake = FakeGemini()
    use_fake(monkeypatch, fake)
    chat = (await client.post("/chats/", json={}, headers=auth)).json()
    for i in range(chat_service.HISTORY_MESSAGES):  # кожен крок додає 2 повідомлення
        await client.post(f"/chats/{chat['id']}/messages", json={"content": f"питання {i}"}, headers=auth)

    sent = texts(fake.calls[-1]["contents"])
    assert len(sent) == chat_service.HISTORY_MESSAGES + 1  # обмежена історія + нове питання
    assert "питання 0" not in sent


async def test_rename_chat(client, auth, other_auth):
    chat = (await client.post("/chats/", json={}, headers=auth)).json()

    resp = await client.patch(f"/chats/{chat['id']}", json={"title": "  Про декоратори  "}, headers=auth)
    assert resp.status_code == 200
    assert resp.json()["title"] == "Про декоратори"
    assert (await client.get(f"/chats/{chat['id']}", headers=auth)).json()["title"] == "Про декоратори"

    assert (await client.patch(f"/chats/{chat['id']}", json={"title": "   "}, headers=auth)).status_code == 422
    assert (await client.patch(f"/chats/{chat['id']}", json={"title": "x" * 201}, headers=auth)).status_code == 422
    # чужий чат недоступний
    assert (await client.patch(f"/chats/{chat['id']}", json={"title": "Хак"}, headers=other_auth)).status_code == 404
