from __future__ import annotations

import socket
from collections.abc import Callable, Iterable
from typing import Any

import httpx
import pytest

from bartleby_core.errors import (
    BlockedHost,
    LinkExtractionFailed,
    LinkTimeout,
    LinkTooLarge,
    LinkUnreachable,
    UnsupportedContentType,
)
from bartleby_core.link_extractor import (
    LinkFetchSettings,
    fetch_and_extract,
)

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"

# A public, non-routable example IP so monkeypatched DNS resolves outside any
# private/loopback/link-local range. 93.184.216.34 (example.com) used to live
# here; we never actually connect.
PUBLIC_STUB_IP = "93.184.216.34"


Handler = Callable[[httpx.Request], httpx.Response]


@pytest.fixture(autouse=True)
def _patch_getaddrinfo(monkeypatch: pytest.MonkeyPatch) -> None:
    """Resolve every hostname to a public IP unless a test overrides this."""

    def _fake(host: str, *_args: object, **_kwargs: object) -> Iterable[tuple[Any, ...]]:
        return [(socket.AF_INET, socket.SOCK_STREAM, 0, "", (PUBLIC_STUB_IP, 0))]

    monkeypatch.setattr(socket, "getaddrinfo", _fake)


def _settings(handler: Handler) -> LinkFetchSettings:
    return LinkFetchSettings(transport=httpx.MockTransport(handler))


# --- happy path -------------------------------------------------------------


async def test_extracts_title_and_markdown() -> None:
    html = """
        <html><head>
          <title>Fallback Title</title>
          <meta property="og:title" content="Real OG Title" />
        </head><body>
          <article>
            <h1>Real OG Title</h1>
            <p>This is a long enough paragraph to satisfy any extractor heuristic
            about minimum article length. We add another sentence so trafilatura
            recognises this as a real article. And another, for good measure.</p>
            <p>Second paragraph with <a href="https://example.com/x">a link</a>.</p>
          </article>
        </body></html>
    """

    def handler(_req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=html, headers={"content-type": "text/html; charset=utf-8"})

    article = await fetch_and_extract(
        "https://example.com/article", settings=_settings(handler)
    )
    assert article.title == "Real OG Title"
    assert "paragraph" in article.markdown.lower()
    assert article.final_url == "https://example.com/article"


async def test_falls_back_to_markdownify_when_trafilatura_returns_nothing() -> None:
    # Tiny page trafilatura will skip; markdownify should still produce *something*.
    html = "<html><head><title>Tiny</title></head><body><p>hi</p></body></html>"

    def handler(_req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=html, headers={"content-type": "text/html"})

    article = await fetch_and_extract("https://example.com/", settings=_settings(handler))
    assert article.title == "Tiny"
    assert "hi" in article.markdown


# --- title fallback chain ---------------------------------------------------


async def test_title_falls_back_to_title_tag() -> None:
    padding = "padding " * 30
    html = (
        "<html><head><title>From Title Tag</title></head>"
        "<body><article><p>Body text long enough to be extracted. "
        f"{padding}</p></article></body></html>"
    )

    def handler(_req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=html, headers={"content-type": "text/html"})

    article = await fetch_and_extract("https://example.com/p", settings=_settings(handler))
    assert article.title == "From Title Tag"


async def test_title_falls_back_to_h1_then_hostname() -> None:
    # No <title>, no og:title, but an <h1>.
    html = "<html><body><h1>Heading One</h1><p>body</p></body></html>"

    def handler(_req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=html, headers={"content-type": "text/html"})

    article = await fetch_and_extract("https://example.com/p", settings=_settings(handler))
    assert article.title == "Heading One"

    # No headings at all → hostname+path.
    html2 = "<html><body><p>just a body</p></body></html>"

    def handler2(_req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=html2, headers={"content-type": "text/html"})

    article2 = await fetch_and_extract(
        "https://example.com/some/path", settings=_settings(handler2)
    )
    assert article2.title == "example.com/some/path"


# --- SSRF guard -------------------------------------------------------------


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/",
        # "localhost" exercises the DNS path; overridden in the test body.
        "http://localhost/",
        "http://192.168.1.1/",
        "http://10.0.0.1/",
        "http://169.254.169.254/",  # AWS metadata link-local
        "http://[::1]/",
        "http://0.0.0.0/",
    ],
)
async def test_blocks_non_public_ip_literals(
    url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    # For literals we never call getaddrinfo, so the autouse stub is irrelevant.
    # For the hostname "localhost" we override the stub to resolve to 127.0.0.1
    # so the guard catches it via the DNS path.
    if "localhost" in url:
        monkeypatch.setattr(
            socket,
            "getaddrinfo",
            lambda *a, **kw: [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("127.0.0.1", 0))],
        )

    def handler(_req: httpx.Request) -> httpx.Response:  # pragma: no cover
        raise AssertionError("guard should run before any HTTP call")

    with pytest.raises(BlockedHost):
        await fetch_and_extract(url, settings=_settings(handler))


async def test_blocks_non_http_schemes() -> None:
    def handler(_req: httpx.Request) -> httpx.Response:  # pragma: no cover
        raise AssertionError("guard should run before any HTTP call")

    for url in ["file:///etc/passwd", "ftp://example.com/", "javascript:alert(1)"]:
        with pytest.raises(BlockedHost):
            await fetch_and_extract(url, settings=_settings(handler))


async def test_blocks_url_with_userinfo() -> None:
    def handler(_req: httpx.Request) -> httpx.Response:  # pragma: no cover
        raise AssertionError("guard should run before any HTTP call")

    with pytest.raises(BlockedHost):
        await fetch_and_extract(
            "http://user:pass@example.com/", settings=_settings(handler)
        )


async def test_blocks_when_dns_resolves_to_private(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *a, **kw: [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("10.0.0.5", 0))],
    )

    def handler(_req: httpx.Request) -> httpx.Response:  # pragma: no cover
        raise AssertionError("guard should run before any HTTP call")

    with pytest.raises(BlockedHost):
        await fetch_and_extract(
            "http://internal.example.com/", settings=_settings(handler)
        )


async def test_blocks_when_dns_resolution_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise(*_args: object, **_kwargs: object) -> list[tuple[Any, ...]]:
        raise OSError("nodename nor servname provided, or not known")

    monkeypatch.setattr(socket, "getaddrinfo", _raise)

    def handler(_req: httpx.Request) -> httpx.Response:  # pragma: no cover
        raise AssertionError("guard should run before any HTTP call")

    with pytest.raises(BlockedHost):
        await fetch_and_extract(
            "http://no-such-host.example/", settings=_settings(handler)
        )


# --- response policies ------------------------------------------------------


async def test_rejects_oversized_response() -> None:
    big = "x" * 200

    def handler(_req: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, text=big, headers={"content-type": "text/html"}
        )

    settings = LinkFetchSettings(
        transport=httpx.MockTransport(handler), max_bytes=50
    )
    with pytest.raises(LinkTooLarge):
        await fetch_and_extract("https://example.com/", settings=settings)


async def test_rejects_non_html_content_type() -> None:
    def handler(_req: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, content=b"%PDF-1.4 ...", headers={"content-type": "application/pdf"}
        )

    with pytest.raises(UnsupportedContentType):
        await fetch_and_extract(
            "https://example.com/file.pdf", settings=_settings(handler)
        )


async def test_404_is_link_unreachable() -> None:
    def handler(_req: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="nope")

    with pytest.raises(LinkUnreachable):
        await fetch_and_extract("https://example.com/missing", settings=_settings(handler))


async def test_timeout_is_link_timeout() -> None:
    def handler(_req: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("timed out")

    with pytest.raises(LinkTimeout):
        await fetch_and_extract("https://example.com/", settings=_settings(handler))


async def test_network_error_is_link_unreachable() -> None:
    def handler(_req: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    with pytest.raises(LinkUnreachable):
        await fetch_and_extract("https://example.com/", settings=_settings(handler))


# --- redirects --------------------------------------------------------------


async def test_follows_redirect_then_extracts() -> None:
    final_html = (
        "<html><head><title>After Redirect</title></head>"
        "<body><article><p>" + ("content " * 40) + "</p></article></body></html>"
    )

    def handler(req: httpx.Request) -> httpx.Response:
        if str(req.url) == "https://example.com/from":
            return httpx.Response(
                301, headers={"location": "https://example.com/to"}
            )
        if str(req.url) == "https://example.com/to":
            return httpx.Response(
                200, text=final_html, headers={"content-type": "text/html"}
            )
        raise AssertionError(f"unexpected url {req.url}")

    article = await fetch_and_extract(
        "https://example.com/from", settings=_settings(handler)
    )
    assert article.title == "After Redirect"
    assert article.final_url == "https://example.com/to"


async def test_too_many_redirects_is_link_unreachable() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        # Always redirect to a new path so we don't hit any de-dup.
        n = int(req.url.path.lstrip("/r") or "0")
        return httpx.Response(302, headers={"location": f"/r{n + 1}"})

    settings = LinkFetchSettings(transport=httpx.MockTransport(handler), max_redirects=2)
    with pytest.raises(LinkUnreachable):
        await fetch_and_extract("https://example.com/r0", settings=settings)


async def test_redirect_into_private_host_is_blocked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {"n": 0}

    def _fake(host: str, *a: object, **kw: object) -> list[tuple[Any, ...]]:
        calls["n"] += 1
        # First call (origin) resolves public; second (redirect target) private.
        ip = PUBLIC_STUB_IP if calls["n"] == 1 else "10.0.0.5"
        return [(socket.AF_INET, socket.SOCK_STREAM, 0, "", (ip, 0))]

    monkeypatch.setattr(socket, "getaddrinfo", _fake)

    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.host == "public.example":
            return httpx.Response(
                302, headers={"location": "http://internal.example/secret"}
            )
        raise AssertionError("redirect target should be blocked before fetch")

    with pytest.raises(BlockedHost):
        await fetch_and_extract(
            "http://public.example/", settings=_settings(handler)
        )


# --- extraction failure -----------------------------------------------------


async def test_extraction_failed_when_body_is_empty() -> None:
    # Empty body — markdownify returns empty, trafilatura returns None.
    def handler(_req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="", headers={"content-type": "text/html"})

    with pytest.raises(LinkExtractionFailed):
        await fetch_and_extract("https://example.com/", settings=_settings(handler))
