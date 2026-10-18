import uuid

import pytest
from sqlalchemy import select

from app import tasks
from app.agent.agent import AgentComment, AgentError, AgentResult
from app.models.comment import ReviewComment
from app.models.review import Review, ReviewStatus


@pytest.fixture
async def review_id(session_factory, client, auth, project_id):
    async with session_factory() as db:
        review = Review(project_id=uuid.UUID(project_id), code_snippet="eval(x)", language="python")
        db.add(review)
        await db.commit()
        return str(review.id)


def fake_agent(monkeypatch, outcome):
    calls = {}

    class FakeAgent:
        async def analyze(self, code, github_url, language, db):
            calls.update(code=code, language=language)
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

    monkeypatch.setattr("app.agent.agent.CodeReviewAgent", FakeAgent)
    return calls


async def _load(session_factory, review_id):
    async with session_factory() as db:
        review = (await db.execute(select(Review).where(Review.id == uuid.UUID(review_id)))).scalar_one()
        comments = (await db.execute(select(ReviewComment).where(ReviewComment.review_id == review.id))).scalars().all()
        return review, comments


async def test_successful_review_is_saved(session_factory, review_id, monkeypatch):
    result = AgentResult(
        overall_score=55,
        summary="ок",
        comments=[AgentComment("security", "critical", 1, "eval", "literal_eval", "OWASP A03:2021" + "x" * 300)],
    )
    calls = fake_agent(monkeypatch, result)

    await tasks._process_review(review_id, session_factory=session_factory)

    review, comments = await _load(session_factory, review_id)
    assert review.status == ReviewStatus.DONE
    assert review.overall_score == 55 and review.completed_at is not None
    assert len(comments) == 1 and len(comments[0].reference) == 255
    assert calls["language"] == "python"  # мова рев'ю доходить до агента


async def test_agent_error_marks_failed_with_user_message(session_factory, review_id, monkeypatch):
    fake_agent(monkeypatch, AgentError("Сервіс AI тимчасово недоступний."))
    await tasks._process_review(review_id, session_factory=session_factory)

    review, comments = await _load(session_factory, review_id)
    assert review.status == ReviewStatus.FAILED
    assert review.error_message == "Сервіс AI тимчасово недоступний."
    assert comments == []


async def test_invalid_github_file_marks_failed(session_factory, review_id, monkeypatch):
    fake_agent(monkeypatch, ValueError("Файл не знайдено: https://github.com/o/r/blob/m/a.py"))
    await tasks._process_review(review_id, session_factory=session_factory)
    review, _ = await _load(session_factory, review_id)
    assert review.status == ReviewStatus.FAILED and "Файл не знайдено" in review.error_message


async def test_unexpected_error_does_not_leak_details(session_factory, review_id, monkeypatch):
    fake_agent(monkeypatch, RuntimeError("password=hunter2 in stack trace"))
    await tasks._process_review(review_id, session_factory=session_factory)

    review, _ = await _load(session_factory, review_id)
    assert review.status == ReviewStatus.FAILED
    assert "hunter2" not in review.error_message


async def test_missing_review_is_ignored(session_factory):
    await tasks._process_review("00000000-0000-0000-0000-000000000000", session_factory=session_factory)
