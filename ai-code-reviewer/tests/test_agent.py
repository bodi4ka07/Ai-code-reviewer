import json
from types import SimpleNamespace

import pytest
from google.genai import errors

from app.agent import agent as agent_module
from app.agent.agent import AgentError, CodeReviewAgent
from app.agent.tools.linter import LintError, LintResult

CODE = "import os\n\ndef f(x):\n    return eval(x)\n"

GOOD = {
    "overall_score": 42,
    "summary": "Є критична проблема.",
    "comments": [
        {
            "category": "security",
            "severity": "critical",
            "line_number": 4,
            "message": "eval",
            "suggestion": "ast.literal_eval",
            "reference": "OWASP A03:2021 - Injection",
        },
        {"category": "style", "severity": "info", "line_number": 999, "message": "m", "suggestion": "s"},
    ],
}


class FakeClient:
    """Підміна Gemini: віддає відповіді/винятки по черзі й запам'ятовує промпти."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.prompts = []
        self.aio = SimpleNamespace(models=SimpleNamespace(generate_content=self._generate))

    async def _generate(self, model, contents, config=None):
        self.prompts.append(contents)
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return SimpleNamespace(text=item if isinstance(item, str) else json.dumps(item))


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    async def instant(_):
        return None

    monkeypatch.setattr(agent_module.asyncio, "sleep", instant)


@pytest.fixture
def lint(monkeypatch):
    async def fake_linter(code, language):
        return LintResult(errors=[LintError(1, "'os' imported but unused", "pyflakes")])

    monkeypatch.setattr(agent_module, "run_linter", fake_linter)


async def test_analyze_parses_and_sanitizes(lint):
    client = FakeClient(GOOD)
    result = await CodeReviewAgent(client).analyze(CODE, None, "python")

    assert result.overall_score == 42
    assert result.comments[0].reference == "OWASP A03:2021 - Injection"
    assert result.comments[0].line_number == 4
    assert result.comments[1].line_number is None  # рядок поза межами коду відкидається


async def test_prompt_is_language_aware_and_contains_lint(lint):
    client = FakeClient(GOOD)
    await CodeReviewAgent(client).analyze(CODE, None, "javascript")
    prompt = client.prompts[0]
    assert "JavaScript" in prompt and "Google JavaScript Style Guide" in prompt
    assert "PEP" not in prompt
    assert "'os' imported but unused" in prompt
    assert "<code_to_review>" in prompt
    assert "зворотні лапки" in prompt  # клієнт показує такі фрагменти моноширинним шрифтом


async def test_prompt_for_unknown_language_is_generic(lint):
    client = FakeClient(GOOD)
    await CodeReviewAgent(client).analyze(CODE, None, "other")
    assert "загальноприйняті практики" in client.prompts[0]


async def test_score_is_clamped(lint):
    result = await CodeReviewAgent(FakeClient({**GOOD, "overall_score": 250})).analyze(CODE, None, "python")
    assert result.overall_score == 100


async def test_invalid_json_fails_instead_of_fake_score(lint):
    with pytest.raises(AgentError, match="розібрати"):
        await CodeReviewAgent(FakeClient("це не json")).analyze(CODE, None, "python")


async def test_unknown_category_fails(lint):
    bad = {**GOOD, "comments": [{**GOOD["comments"][0], "category": "magic"}]}
    with pytest.raises(AgentError):
        await CodeReviewAgent(FakeClient(bad)).analyze(CODE, None, "python")


async def test_fenced_json_is_accepted(lint):
    result = await CodeReviewAgent(FakeClient("```json\n" + json.dumps(GOOD) + "\n```")).analyze(CODE, None, "python")
    assert result.overall_score == 42


async def test_transient_error_is_retried(lint):
    client = FakeClient(errors.ServerError(503, {"error": {"message": "overloaded"}}), GOOD)
    result = await CodeReviewAgent(client).analyze(CODE, None, "python")
    assert result.overall_score == 42
    assert len(client.prompts) == 2


async def test_persistent_error_gives_user_safe_message(lint):
    err = errors.ServerError(503, {"error": {"message": "internal secret"}})
    with pytest.raises(AgentError) as exc:
        await CodeReviewAgent(FakeClient(err, err, err)).analyze(CODE, None, "python")
    assert "secret" not in str(exc.value)


async def test_client_error_is_not_retried(lint):
    client = FakeClient(errors.ClientError(400, {"error": {"message": "bad request"}}))
    with pytest.raises(AgentError):
        await CodeReviewAgent(client).analyze(CODE, None, "python")
    assert len(client.prompts) == 1


async def test_rag_failure_does_not_break_review(lint, monkeypatch, caplog):
    async def broken_search(*args, **kwargs):
        raise RuntimeError("pgvector missing")

    monkeypatch.setattr(agent_module, "search_docs", broken_search)
    result = await CodeReviewAgent(FakeClient(GOOD)).analyze(CODE, None, "python", db=object())
    assert result.overall_score == 42
    assert "RAG-пошук не вдався" in caplog.text  # помилка тепер видима в логах


async def test_rag_context_reaches_prompt(lint, monkeypatch):
    from app.agent.tools.rag_search import DocChunk

    async def fake_search(query, db, language, limit):
        assert language == "python"
        assert "imported but unused" in query  # запит залежить від результатів лінтера
        return [DocChunk("OWASP Top 10", "A03:2021 Injection ...")]

    monkeypatch.setattr(agent_module, "search_docs", fake_search)
    client = FakeClient(GOOD)
    await CodeReviewAgent(client).analyze(CODE, None, "python", db=object())
    assert "[OWASP Top 10]" in client.prompts[0]


async def test_analyze_fetches_github_code(lint, monkeypatch):
    async def fake_fetch(url):
        return CODE

    monkeypatch.setattr(agent_module, "fetch_github_file", fake_fetch)
    result = await CodeReviewAgent(FakeClient(GOOD)).analyze(None, "https://github.com/o/r/blob/m/a.py", "python")
    assert result.overall_score == 42


async def test_analyze_without_source_fails():
    with pytest.raises(AgentError):
        await CodeReviewAgent(FakeClient()).analyze(None, None, "python")
