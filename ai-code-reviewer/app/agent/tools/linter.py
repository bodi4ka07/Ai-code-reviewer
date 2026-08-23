import subprocess
import tempfile
import os
from dataclasses import dataclass


@dataclass
class LintError:
    line: int
    column: int
    code: str
    message: str


def run_linter(code: str, language: str = "python") -> list[LintError]:
    """
    Запускає pylint на коді і повертає список помилок.
    """
    if language != "python":
        return []

    errors = []

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        tmp_path = f.name

    try:
        result = subprocess.run(
            [
                "python", "-m", "pyflakes", tmp_path
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        for line in result.stdout.splitlines():
            # pyflakes формат: filename:line: message
            parts = line.split(":", 2)
            if len(parts) >= 3:
                try:
                    line_num = int(parts[1].strip())
                    message = parts[2].strip()
                    errors.append(LintError(
                        line=line_num,
                        column=0,
                        code="W",
                        message=message,
                    ))
                except ValueError:
                    continue

    except subprocess.TimeoutExpired:
        errors.append(LintError(line=0, column=0, code="E", message="Лінтер завис — код занадто великий"))
    except Exception as e:
        errors.append(LintError(line=0, column=0, code="E", message=f"Помилка лінтера: {str(e)}"))
    finally:
        os.unlink(tmp_path)

    return errors


def format_lint_results(errors: list[LintError]) -> str:
    """
    Форматує результати лінтера в текст для AI-агента.
    """
    if not errors:
        return "Лінтер не знайшов синтаксичних помилок."

    lines = ["Знайдені проблеми лінтером:"]
    for err in errors:
        if err.line > 0:
            lines.append(f"  Рядок {err.line}: {err.message}")
        else:
            lines.append(f"  {err.message}")

    return "\n".join(lines)