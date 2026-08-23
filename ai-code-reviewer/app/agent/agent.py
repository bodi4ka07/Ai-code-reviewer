import json
from google import genai
from app.core.config import settings
from app.agent.tools.linter import run_linter, format_lint_results
from app.agent.tools.github_fetcher import fetch_github_file
from app.agent.tools.rag_search import search_docs, format_rag_context
from dataclasses import dataclass


@dataclass
class AgentComment:
    category: str
    severity: str
    line_number: int | None
    message: str
    suggestion: str


@dataclass
class AgentResult:
    overall_score: int
    summary: str
    comments: list[AgentComment]


class CodeReviewAgent:
    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)

    async def analyze(self, code: str | None, github_url: str | None, language: str = "python", db=None) -> AgentResult:
        # Крок 1: отримуємо код
        if github_url and not code:
            code = await fetch_github_file(github_url)

        if not code:
            raise ValueError("Немає коду для аналізу")

        # Крок 2: запускаємо лінтер
        lint_errors = run_linter(code, language)
        lint_report = format_lint_results(lint_errors)

        # Крок 3: RAG пошук по документації
        rag_context = ""
        if db:
            try:
                chunks = await search_docs(
                    query=f"code review best practices {language} security bugs",
                    db=db,
                    limit=4,
                )
                rag_context = await format_rag_context(chunks)
            except Exception:
                rag_context = ""

        # Крок 4: формуємо промпт
        prompt = self._build_prompt(code, lint_report, rag_context, language)

        # Крок 5: відправляємо в Gemini
        response = self.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        raw_text = response.text

        # Крок 6: парсимо відповідь
        return self._parse_response(raw_text)

    def _build_prompt(self, code: str, lint_report: str, rag_context: str, language: str) -> str:
        return f"""Ти — досвідчений senior розробник який робить code review.
Проаналізуй наданий {language} код і надай детальний звіт.

РЕЗУЛЬТАТИ ЛІНТЕРА:
{lint_report}

{rag_context}

КОД ДЛЯ АНАЛІЗУ:
```{language}
{code}
```

Знайди проблеми в цих категоріях:
- bug: логічні помилки, некоректна поведінка
- security: вразливості безпеки (SQL ін'єкції, XSS, незахищені дані)
- style: порушення стандартів коду (PEP8 для Python)
- performance: неефективний код, зайві операції

ВАЖЛИВО: Відповідай ТІЛЬКИ валідним JSON без жодного тексту до або після. Формат:
{{
  "overall_score": <число від 0 до 100>,
  "summary": "<загальний опис якості коду, 2-3 речення>",
  "comments": [
    {{
      "category": "<bug|security|style|performance>",
      "severity": "<critical|warning|info>",
      "line_number": <номер рядка або null>,
      "message": "<опис проблеми>",
      "suggestion": "<конкретна порада як виправити>"
    }}
  ]
}}"""

    def _parse_response(self, raw_text: str) -> AgentResult:
        text = raw_text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1])

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return AgentResult(
                overall_score=50,
                summary="Не вдалось розпарсити відповідь AI. Спробуйте ще раз.",
                comments=[],
            )

        comments = []
        for c in data.get("comments", []):
            category = c.get("category", "style")
            if category not in ("bug", "security", "style", "performance"):
                category = "style"

            severity = c.get("severity", "info")
            if severity not in ("critical", "warning", "info"):
                severity = "info"

            comments.append(AgentComment(
                category=category,
                severity=severity,
                line_number=c.get("line_number"),
                message=c.get("message", ""),
                suggestion=c.get("suggestion", ""),
            ))

        return AgentResult(
            overall_score=max(0, min(100, data.get("overall_score", 50))),
            summary=data.get("summary", ""),
            comments=comments,
        )