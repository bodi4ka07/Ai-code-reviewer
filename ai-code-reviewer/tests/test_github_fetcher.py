import httpx
import pytest

from app.agent.tools.github_fetcher import fetch_github_file, parse_github_url


def test_parse_blob_url():
    f = parse_github_url("https://github.com/owner/repo/blob/main/src/app/main.py")
    assert (f.owner, f.repo, f.ref, f.path) == ("owner", "repo", "main", "src/app/main.py")
    assert f.raw_url == "https://raw.githubusercontent.com/owner/repo/main/src/app/main.py"


def test_parse_raw_url():
    f = parse_github_url("https://raw.githubusercontent.com/owner/repo/main/a/b.js")
    assert f.path == "a/b.js"


@pytest.mark.parametrize(
    "url",
    [
        "https://evil.com/owner/repo/blob/main/a.py",
        "http://github.com/owner/repo/blob/main/a.py",
        "https://github.com.evil.com/owner/repo/blob/main/a.py",
        "https://evil.com/github.com/owner/repo/blob/main/a.py",
        "https://github.com@evil.com/owner/repo/blob/main/a.py",
        "https://user:pw@github.com/owner/repo/blob/main/a.py",
        "https://github.com:8443/owner/repo/blob/main/a.py",
        "https://github.com/owner/repo/tree/main/src",
        "https://github.com/owner/repo",
        "https://github.com/owner/repo/blob/main/../../etc/passwd",
        "https://github.com/owner/repo/blob/main/%2e%2e/secret",
        "file:///etc/passwd",
        "http://169.254.169.254/latest/meta-data",
        "http://localhost:6379",
        "not a url",
        "",
    ],
)
def test_parse_rejects_unsafe_urls(url):
    with pytest.raises(ValueError):
        parse_github_url(url)


def _client(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_fetch_requests_only_raw_host():
    seen = []

    def handler(request: httpx.Request):
        seen.append(str(request.url))
        return httpx.Response(200, text="print('hi')")

    code = await fetch_github_file("https://github.com/o/r/blob/main/a.py", client=_client(handler))
    assert code == "print('hi')"
    assert seen == ["https://raw.githubusercontent.com/o/r/main/a.py"]


async def test_fetch_never_sends_authorization(monkeypatch):
    """Спільний токен сервера не має потрапляти в запити: інакше користувачі читали б чужі приватні файли."""
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_should_never_be_sent")
    headers = {}

    def handler(request: httpx.Request):
        headers.update(request.headers)
        return httpx.Response(200, text="x = 1")

    await fetch_github_file("https://github.com/o/r/blob/main/a.py", client=_client(handler))
    assert "authorization" not in headers


@pytest.mark.parametrize("status, fragment", [(404, "приватний"), (403, "приватний"), (500, "HTTP 500")])
async def test_fetch_error_statuses(status, fragment):
    client = _client(lambda request: httpx.Response(status))
    with pytest.raises(ValueError, match=fragment):
        await fetch_github_file("https://github.com/o/r/blob/main/a.py", client=client)


async def test_fetch_rejects_oversized_file():
    client = _client(lambda request: httpx.Response(200, text="x" * 20001))
    with pytest.raises(ValueError, match="занадто великий"):
        await fetch_github_file("https://github.com/o/r/blob/main/a.py", client=client)


async def test_fetch_network_error_is_user_safe():
    def handler(request):
        raise httpx.ConnectError("secret internal detail")

    with pytest.raises(ValueError) as exc:
        await fetch_github_file("https://github.com/o/r/blob/main/a.py", client=_client(handler))
    assert "secret" not in str(exc.value)
