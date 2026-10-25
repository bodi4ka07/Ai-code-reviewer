import uuid
from types import SimpleNamespace

from app.models.comment import CommentCategory, CommentSeverity, ReviewComment
from app.models.review import Review, ReviewStatus

CODE = "def f(x):\n    return eval(x)\n"


async def test_create_review_with_code(client, auth, project_id, queued):
    resp = await client.post("/reviews/", json={"project_id": project_id, "code_snippet": CODE}, headers=auth)
    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "pending"
    assert body["language"] == "python"  # успадковано від проєкту
    assert queued == [body["id"]]


async def test_review_language_override_and_detection(client, auth, project_id):
    explicit = await client.post(
        "/reviews/", json={"project_id": project_id, "code_snippet": CODE, "language": "javascript"}, headers=auth
    )
    assert explicit.json()["language"] == "javascript"

    detected = await client.post(
        "/reviews/",
        json={"project_id": project_id, "github_url": "https://github.com/o/r/blob/main/src/app.ts"},
        headers=auth,
    )
    assert detected.json()["language"] == "typescript"


async def test_create_review_requires_source(client, auth, project_id):
    resp = await client.post("/reviews/", json={"project_id": project_id}, headers=auth)
    assert resp.status_code == 422


async def test_create_review_rejects_non_github_url(client, auth, project_id, queued):
    for url in (
        "https://evil.com/o/r/blob/main/a.py",
        "http://github.com/o/r/blob/main/a.py",
        "https://github.com.evil.com/o/r/blob/main/a.py",
        "http://169.254.169.254/latest/meta-data",
    ):
        resp = await client.post("/reviews/", json={"project_id": project_id, "github_url": url}, headers=auth)
        assert resp.status_code == 422, url
    assert queued == []


async def test_create_review_rejects_oversized_code(client, auth, project_id):
    resp = await client.post(
        "/reviews/", json={"project_id": project_id, "code_snippet": "x" * 20001}, headers=auth
    )
    assert resp.status_code == 422


async def test_cannot_review_foreign_project(client, other_auth, project_id, queued):
    resp = await client.post("/reviews/", json={"project_id": project_id, "code_snippet": CODE}, headers=other_auth)
    assert resp.status_code == 404
    assert queued == []


async def test_queue_failure_marks_review_failed(client, auth, project_id, monkeypatch):
    def boom(_):
        raise ConnectionError("redis down")

    monkeypatch.setattr("app.api.routes.reviews.process_review_task.delay", boom)
    resp = await client.post("/reviews/", json={"project_id": project_id, "code_snippet": CODE}, headers=auth)
    assert resp.status_code == 202
    assert resp.json()["status"] == "failed"
    assert "redis" not in resp.json()["error_message"].lower()


async def test_review_detail_contains_code(client, auth, project_id):
    rid = (await client.post("/reviews/", json={"project_id": project_id, "code_snippet": CODE}, headers=auth)).json()["id"]
    body = (await client.get(f"/reviews/{rid}", headers=auth)).json()
    assert body["code_snippet"] == CODE
    assert body["github_url"] is None


async def test_get_review_and_ownership(client, auth, other_auth, project_id):
    rid = (await client.post("/reviews/", json={"project_id": project_id, "code_snippet": CODE}, headers=auth)).json()["id"]
    assert (await client.get(f"/reviews/{rid}", headers=auth)).status_code == 200
    assert (await client.get(f"/reviews/{rid}", headers=other_auth)).status_code == 404
    assert (await client.get(f"/reviews/{uuid.uuid4()}", headers=auth)).status_code == 404


async def test_project_review_history(client, auth, project_id):
    for _ in range(2):
        await client.post("/reviews/", json={"project_id": project_id, "code_snippet": CODE}, headers=auth)
    resp = await client.get(f"/projects/{project_id}/reviews", headers=auth)
    assert resp.status_code == 200
    assert len(resp.json()) == 2


async def _done_review(session_factory, project_id):
    async with session_factory() as db:
        review = Review(
            project_id=uuid.UUID(project_id), code_snippet=CODE, status=ReviewStatus.DONE, overall_score=40, summary="погано"
        )
        db.add(review)
        await db.flush()
        comment = ReviewComment(
            review_id=review.id,
            category=CommentCategory.SECURITY,
            severity=CommentSeverity.CRITICAL,
            line_number=2,
            message="eval",
            suggestion="literal_eval",
            reference="OWASP A03:2021",
        )
        db.add(comment)
        await db.commit()
        return str(review.id), str(comment.id)


class FakeGemini:
    def __init__(self):
        self.prompts = []
        self.aio = SimpleNamespace(models=SimpleNamespace(generate_content=self._generate))

    async def _generate(self, model, contents, config=None):
        self.prompts.append(contents)
        return SimpleNamespace(text="Відповідь AI")


async def test_ask_requires_finished_review(client, auth, project_id):
    rid = (await client.post("/reviews/", json={"project_id": project_id, "code_snippet": CODE}, headers=auth)).json()["id"]
    resp = await client.post(f"/reviews/{rid}/ask", json={"question": "чому?"}, headers=auth)
    assert resp.status_code == 400


async def test_ask_about_comment(client, auth, project_id, session_factory, monkeypatch):
    fake = FakeGemini()
    monkeypatch.setattr("google.genai.Client", lambda api_key: fake)
    rid, cid = await _done_review(session_factory, project_id)

    resp = await client.post(
        f"/reviews/{rid}/ask", json={"question": "чому це погано?", "comment_id": cid}, headers=auth
    )
    assert resp.status_code == 200
    assert resp.json() == {"answer": "Відповідь AI"}
    assert "КОНКРЕТНОГО КОМЕНТАРЯ" in fake.prompts[0]
    assert "literal_eval" in fake.prompts[0]


async def test_ask_unknown_comment(client, auth, project_id, session_factory, monkeypatch):
    monkeypatch.setattr("google.genai.Client", lambda api_key: FakeGemini())
    rid, _ = await _done_review(session_factory, project_id)
    resp = await client.post(
        f"/reviews/{rid}/ask", json={"question": "?", "comment_id": str(uuid.uuid4())}, headers=auth
    )
    assert resp.status_code == 404


async def test_ask_validates_question_length(client, auth, project_id, session_factory):
    rid, _ = await _done_review(session_factory, project_id)
    resp = await client.post(f"/reviews/{rid}/ask", json={"question": "x" * 1001}, headers=auth)
    assert resp.status_code == 422
