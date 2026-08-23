import httpx
import re
from app.core.config import settings


def parse_github_url(url: str) -> tuple[str, str, str] | None:
    """
    Парсить GitHub URL і повертає (owner, repo, path).
    Підтримує формати:
    - https://github.com/owner/repo/blob/branch/path/to/file.py
    - https://raw.githubusercontent.com/owner/repo/branch/path/to/file.py
    """
    # raw.githubusercontent.com
    raw_pattern = r"https://raw\.githubusercontent\.com/([^/]+)/([^/]+)/[^/]+/(.+)"
    match = re.match(raw_pattern, url)
    if match:
        return match.group(1), match.group(2), match.group(3)

    # github.com/blob
    blob_pattern = r"https://github\.com/([^/]+)/([^/]+)/blob/[^/]+/(.+)"
    match = re.match(blob_pattern, url)
    if match:
        return match.group(1), match.group(2), match.group(3)

    return None


async def fetch_github_file(url: str) -> str:
    """
    Завантажує вміст файлу з GitHub.
    """
    parsed = parse_github_url(url)

    headers = {}
    if settings.GITHUB_TOKEN and settings.GITHUB_TOKEN != "your-github-token-here":
        headers["Authorization"] = f"token {settings.GITHUB_TOKEN}"

    # Конвертуємо в raw URL якщо потрібно
    if "github.com" in url and "/blob/" in url:
        raw_url = url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
    else:
        raw_url = url

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(raw_url, headers=headers)

        if response.status_code == 404:
            raise ValueError(f"Файл не знайдено: {url}")
        elif response.status_code == 403:
            raise ValueError("Доступ заборонено. Для приватних репо потрібен GITHUB_TOKEN.")
        elif response.status_code != 200:
            raise ValueError(f"Помилка завантаження: HTTP {response.status_code}")

        content = response.text

        # Обмеження розміру — не більше 10000 символів
        if len(content) > 10000:
            content = content[:10000] + "\n\n... (файл обрізано, занадто великий)"

        return content