import json
import shutil

import pytest

from app.agent.tools import linter
from app.agent.tools.linter import LintResult, format_lint_results, parse_pyflakes, parse_semgrep, run_linter
from app.core.languages import detect_language, normalize_language


def test_parse_pyflakes_output():
    out = "code.py:1:1: 'os' imported but unused\ncode.py:4:5: undefined name 'x'\n"
    errors = parse_pyflakes(out)
    assert [(e.line, e.message) for e in errors] == [(1, "'os' imported but unused"), (4, "undefined name 'x'")]


def test_parse_pyflakes_syntax_error():
    errors = parse_pyflakes("code.py:3:5: invalid syntax\n    foo(\n")
    assert errors[0].line == 3


def test_parse_semgrep_output():
    payload = {
        "results": [
            {
                "check_id": "py-eval-exec",
                "start": {"line": 7},
                "extra": {
                    "severity": "ERROR",
                    "message": "eval() виконує довільний код.",
                    "metadata": {"category": "security", "owasp": "A03:2021 - Injection", "fix": "literal_eval"},
                },
            }
        ]
    }
    (e,) = parse_semgrep(json.dumps(payload))
    assert (e.line, e.severity, e.category, e.reference) == (7, "critical", "security", "A03:2021 - Injection")
    assert "literal_eval" in e.message


async def test_unsupported_language_is_ai_only():
    result = await run_linter("print(1)", "other")
    assert result.errors == []
    assert "лише AI" in result.notes[0]


async def test_pyflakes_finds_unused_import(monkeypatch):
    monkeypatch.setattr(linter.settings, "SEMGREP_BIN", "definitely-not-installed")
    result = await run_linter("import os\n", "python")
    assert any("imported but unused" in e.message for e in result.errors)
    assert any("Semgrep недоступний" in n for n in result.notes)  # відсутність Semgrep не ламає аналіз


async def test_pyflakes_reports_syntax_error(monkeypatch):
    monkeypatch.setattr(linter.settings, "SEMGREP_BIN", "definitely-not-installed")
    result = await run_linter("def broken(:\n    pass\n", "python")
    assert result.errors and result.errors[0].tool == "pyflakes"


async def test_linter_never_executes_code(monkeypatch, tmp_path):
    monkeypatch.setattr(linter.settings, "SEMGREP_BIN", "definitely-not-installed")
    marker = tmp_path / "pwned"
    await run_linter(f"open(r'{marker}', 'w').write('x')\n", "python")
    assert not marker.exists()


def test_source_filename_cannot_shadow_stdlib():
    import sys

    assert linter.SOURCE_STEM not in sys.stdlib_module_names


def test_format_lint_results():
    assert "не знайшов" in format_lint_results(LintResult())
    text = format_lint_results(LintResult(errors=[linter.LintError(3, "msg", "semgrep", "critical", reference="OWASP")]))
    assert "Рядок 3" in text and "[OWASP]" in text


@pytest.mark.skipif(shutil.which(linter.settings.SEMGREP_BIN) is None, reason="semgrep не встановлено (працює в Docker)")
@pytest.mark.parametrize(
    "language, code, rule_hint",
    [
        ("python", 'def f(c, n):\n    c.execute("SELECT * FROM u WHERE n=\'" + n + "\'")\n    return eval(n)\n', "SQL-запит"),
        ("javascript", "const r = eval(userInput);\n", "eval"),
    ],
)
async def test_semgrep_rules_detect_known_issues(language, code, rule_hint):
    result = await run_linter(code, language)
    assert any(e.tool == "semgrep" and rule_hint in e.message for e in result.errors), (result.errors, result.notes)


@pytest.mark.skipif(shutil.which(linter.settings.SEMGREP_BIN) is None, reason="semgrep не встановлено (працює в Docker)")
async def test_var_rule_flags_only_var_not_const_or_let():
    # Шаблон Semgrep `var $X = ...` сам по собі спрацьовує й на const та let (хибні спрацювання)
    code = 'const a = 1;\nlet b = 2;\nvar c = 3;\nconst s = "var z = 1";\n'
    result = await run_linter(code, "javascript")
    var_lines = [e.line for e in result.errors if "var" in e.message and e.tool == "semgrep"]
    assert var_lines == [3], (result.errors, result.notes)


def test_language_helpers():
    assert normalize_language("TS") == "typescript"
    assert normalize_language("other") == "other"
    with pytest.raises(ValueError):
        normalize_language("brainfuck")
    assert detect_language("src/App.tsx") == "typescript"
    assert detect_language("notes.txt") is None
