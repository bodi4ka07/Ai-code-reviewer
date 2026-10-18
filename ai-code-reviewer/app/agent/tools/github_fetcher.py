import re
from dataclasses import dataclass
from urllib.parse import quote, unquote, urlsplit

import httpx

from app.core.config import settings

RAW_HOST = "raw.githubusercontent.com"
ALLOWED_HOSTS = {"github.com", "www.github.com", RAW_HOST}

_NAME_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
_SEGMENT_RE = re.compile(r"^[^/\\\x00-\x1f]+$")


@dataclass(frozen=True)
class GithubFile:
    owner: str
    repo: str
    ref: str
    path: str

    @property
    def raw_url(self) -> str:
        # URL збирається з перевірених частин, а не береться від користувача
        path = "/".join(quote(seg, safe="") for seg in self.path.split("/"))
        return f"https://{RAW_HOST}/{self.owner}/{self.repo}/{self.ref}/{path}"


def parse_github_url(url: str) -> GithubFile:
    """
    Розбирає посилання на файл GitHub. Кидає ValueError для будь-чого іншого.

    Підтримує:
    - https://github.com/owner/repo/blob/branch/path/to/file.py
    - https://raw.githubusercontent.com/owner/repo/branch/path/to/file.py
    """
    try:
        parts = urlsplit(url.strip())
        port = parts.port
    except ValueError:
        raise ValueError("Некоректне посилання")

    host = (parts.hostname or "").lower()
    if parts.scheme != "https" or host not in ALLOWED_HOSTS:
        raise ValueError("Дозволені лише https-посилання на github.com та raw.githubusercontent.com")
    if parts.username or parts.password or port not in (None, 443):
        raise ValueError("Некоректне посилання")

    segments = [unquote(s) for s in parts.path.split("/") if s]
    if host == RAW_HOST:
        if len(segments) < 4:
            raise ValueError("Посилання має вказувати на файл")
        owner, repo, ref, *path = segments
    else:
        if len(segments) < 5 or segments[2] != "blob":
            raise ValueError("Посилання має мати вигляд github.com/owner/repo/blob/branch/path")
        owner, repo, _, ref, *path = segments

    if not (_NAME_RE.match(owner) and _NAME_RE.match(repo) and _NAME_RE.match(ref)):
        raise ValueError("Некоректне посилання")
    if any(seg in (".", "..") or not _SEGMENT_RE.match(seg) for seg in path):
        raise ValueError("Некоректний шлях до файлу")

    return GithubFile(owner=owner, repo=repo, ref=ref, path="/".join(path))


async def fetch_github_file(url: str, client: httpx.AsyncClient | None = None) -> str:
    """Завантажує вміст файлу з GitHub. Кидає ValueError з повідомленням для користувача."""
    gh = parse_github_url(url)

    headers = {}
    if settings.GITHUB_TOKEN and settings.GITHUB_TOKEN != "your-github-token-here":
        headers["Authorization"] = f"token {settings.GITHUB_TOKEN}"

    max_bytes = settings.MAX_CODE_CHARS * 4
    own_client = client is None
    client = client or httpx.AsyncClient(timeout=15.0, follow_redirects=False)

    try:
        async with client.stream("GET", gh.raw_url, headers=headers) as response:
            if response.status_code == 404:
                raise ValueError(f"Файл не знайдено: {url}")
            if response.status_code in (401, 403):
                raise ValueError("Доступ заборонено. Для приватних репозиторіїв потрібен GITHUB_TOKEN.")
            if response.status_code != 200:
                raise ValueError(f"Помилка завантаження з GitHub: HTTP {response.status_code}")

            body = bytearray()
            async for chunk in response.aiter_bytes():
                body.extend(chunk)
                if len(body) > max_bytes:
                    raise ValueError("Файл занадто великий для аналізу")
    except httpx.HTTPError:
        raise ValueError("Не вдалося звернутися до GitHub. Спробуйте пізніше.")
    finally:
        if own_client:
            await client.aclose()

    try:
        content = body.decode("utf-8")
    except UnicodeDecodeError:
        raise ValueError("Файл не є текстовим UTF-8")

    if len(content) > settings.MAX_CODE_CHARS:
        raise ValueError(f"Файл занадто великий (максимум {settings.MAX_CODE_CHARS} символів)")
    return content
