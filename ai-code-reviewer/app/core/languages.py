"""Мови, які підтримує рев'ювер.

Для кожної мови є правила Semgrep (app/agent/rules) і стандарт стилю для промпту.
Усе інше обробляється в режимі "other": без статичного аналізу, лише AI.
"""
from dataclasses import dataclass
from pathlib import PurePosixPath

OTHER = "other"


@dataclass(frozen=True)
class Language:
    code: str
    name: str
    extensions: tuple[str, ...]
    style_guide: str
    rules_file: str
    use_pyflakes: bool = False


LANGUAGES: dict[str, Language] = {
    "python": Language(
        code="python",
        name="Python",
        extensions=(".py",),
        style_guide="PEP 8",
        rules_file="python.yml",
        use_pyflakes=True,
    ),
    "javascript": Language(
        code="javascript",
        name="JavaScript",
        extensions=(".js", ".jsx", ".mjs", ".cjs"),
        style_guide="Google JavaScript Style Guide",
        rules_file="javascript.yml",
    ),
    "typescript": Language(
        code="typescript",
        name="TypeScript",
        extensions=(".ts", ".tsx"),
        style_guide="Google TypeScript Style Guide",
        rules_file="javascript.yml",
    ),
}

_ALIASES = {"py": "python", "js": "javascript", "ts": "typescript"}


def normalize_language(value: str) -> str:
    """Приводить код мови до канонічного вигляду або кидає ValueError."""
    code = _ALIASES.get(value.strip().lower(), value.strip().lower())
    if code in LANGUAGES or code == OTHER:
        return code
    allowed = ", ".join([*LANGUAGES, OTHER])
    raise ValueError(f"Непідтримувана мова '{value}'. Доступні: {allowed}")


def get_language(code: str) -> Language | None:
    return LANGUAGES.get(code)


def detect_language(path: str) -> str | None:
    """Визначає мову за розширенням файлу; None, якщо розширення невідоме."""
    suffix = PurePosixPath(path).suffix.lower()
    for lang in LANGUAGES.values():
        if suffix in lang.extensions:
            return lang.code
    return None
