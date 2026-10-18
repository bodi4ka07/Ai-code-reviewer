"""Статичний аналіз коду. Інструменти лише читають код і ніколи його не виконують."""
import asyncio
import json
import re
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from app.core.config import settings
from app.core.languages import get_language

RULES_DIR = Path(__file__).resolve().parent.parent / "rules"
TIMEOUT_SECONDS = 30

_PYFLAKES_RE = re.compile(r"^code\.py:(\d+):(?:(\d+):?)?\s*(.*)$")
_SEMGREP_SEVERITY = {"ERROR": "critical", "WARNING": "warning", "INFO": "info"}


@dataclass
class LintError:
    line: int
    message: str
    tool: str
    severity: str = "warning"
    category: str | None = None
    reference: str | None = None


@dataclass
class LintResult:
    errors: list[LintError] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


async def _run(args: list[str], cwd: Path) -> tuple[int, str, str]:
    proc = await asyncio.create_subprocess_exec(
        *args,
        cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise
    return proc.returncode, stdout.decode("utf-8", "replace"), stderr.decode("utf-8", "replace")


def parse_pyflakes(output: str) -> list[LintError]:
    errors = []
    for raw in output.splitlines():
        m = _PYFLAKES_RE.match(raw.strip())
        if m:
            errors.append(LintError(line=int(m.group(1)), message=m.group(3), tool="pyflakes"))
    return errors


def parse_semgrep(output: str) -> list[LintError]:
    data = json.loads(output)
    errors = []
    for r in data.get("results", []):
        extra = r.get("extra", {})
        meta = extra.get("metadata", {}) or {}
        message = extra.get("message", "")
        if meta.get("fix"):
            message = f"{message} Порада: {meta['fix']}."
        errors.append(
            LintError(
                line=r.get("start", {}).get("line", 0),
                message=message,
                tool="semgrep",
                severity=_SEMGREP_SEVERITY.get(extra.get("severity", ""), "warning"),
                category=meta.get("category"),
                reference=meta.get("owasp") or meta.get("reference"),
            )
        )
    return errors


async def run_linter(code: str, language: str) -> LintResult:
    result = LintResult()
    lang = get_language(language)
    if lang is None:
        result.notes.append("Статичний аналіз для цієї мови недоступний, виконано лише AI-аналіз.")
        return result

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        source = tmp_dir / f"code{lang.extensions[0]}"
        source.write_text(code, encoding="utf-8")

        if lang.use_pyflakes:
            try:
                _, out, err = await _run([sys.executable, "-m", "pyflakes", source.name], tmp_dir)
                result.errors += parse_pyflakes(out + "\n" + err)
            except asyncio.TimeoutError:
                result.notes.append("pyflakes перевищив ліміт часу.")
            except OSError as e:
                result.notes.append(f"pyflakes недоступний: {e}")

        rules = RULES_DIR / lang.rules_file
        try:
            _, out, err = await _run(
                [
                    settings.SEMGREP_BIN, "scan",
                    "--config", str(rules),
                    "--json", "--quiet",
                    "--metrics=off", "--disable-version-check",
                    source.name,
                ],
                tmp_dir,
            )
            result.errors += parse_semgrep(out)
        except asyncio.TimeoutError:
            result.notes.append("Semgrep перевищив ліміт часу.")
        except (OSError, json.JSONDecodeError):
            result.notes.append("Semgrep недоступний або повернув некоректний результат.")

    result.errors.sort(key=lambda e: e.line)
    return result


def format_lint_results(result: LintResult) -> str:
    """Форматує результати лінтера в текст для промпта."""
    lines = []
    if result.errors:
        lines.append("Знайдено статичним аналізом:")
        for e in result.errors:
            where = f"Рядок {e.line}" if e.line > 0 else "Загальне"
            ref = f" [{e.reference}]" if e.reference else ""
            lines.append(f"  - {where} ({e.tool}, {e.severity}): {e.message}{ref}")
    else:
        lines.append("Статичний аналіз не знайшов проблем.")
    lines += [f"Примітка: {n}" for n in result.notes]
    return "\n".join(lines)
