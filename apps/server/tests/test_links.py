from __future__ import annotations

import socket
from collections.abc import Callable, Iterator
from typing import cast

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from engram_core import LinkFetchSettings, LinkService
from engram_server.service import get_link_service, get_service

Handler = Callable[[httpx.Request], httpx.Response]

ARTICLE_HTML = """
<html><head>
  <title>Test Article</title>
  <meta property="og:title" content="A Real Title" />
</head><body>
  <article>
    <h1>A Real Title</h1>
    <p>Engram ingests a URL and stores the extracted article in the vault as
    Markdown. This paragraph exists so trafilatura's heuristics consider the
    page meaningful enough to extract. Another sentence, for length.</p>
    <p>Second paragraph with a <a href="https://example.com/x">link</a>.</p>
  </article>
</body></html>
"""


@pytest.fixture(autouse=True)
def _patch_dns(monkeypatch: pytest.MonkeyPatch) -> None:
    """Resolve any host to a public IP so the SSRF guard allows the request.
    Tests that exercise the guard override this individually.
    """
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *a, **kw: [
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", 0))
        ],
    )


def _override_link_service(client: TestClient, handler: Handler) -> Iterator[None]:
    """Swap the FastAPI ``get_link_service`` dependency for a service whose
    extractor uses an injected ``httpx.MockTransport``.
    """
    settings = LinkFetchSettings(transport=httpx.MockTransport(handler))
    app = cast(FastAPI, client.app)

    def _provider() -> LinkService:
        return LinkService(get_service(), fetch_settings=settings)

    app.dependency_overrides[get_link_service] = _provider
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_link_service, None)


@pytest.fixture
def mocked_link(client: TestClient, request: pytest.FixtureRequest) -> Iterator[None]:
    """Indirect-parametrized fixture: takes a handler, installs the override."""
    handler: Handler = request.param
    yield from _override_link_service(client, handler)


# --- happy path -------------------------------------------------------------


@pytest.mark.parametrize(
    "mocked_link",
    [
        lambda _req: httpx.Response(
            200, text=ARTICLE_HTML, headers={"content-type": "text/html"}
        )
    ],
    indirect=True,
)
def test_create_link_returns_201_with_note(
    mocked_link: None, client: TestClient, auth: dict[str, str]
) -> None:
    r = client.post(
        "/api/v1/links",
        headers=auth,
        json={"url": "https://example.com/article"},
    )
    assert r.status_code == 201, r.text
    note = r.json()
    assert note["title"] == "A Real Title"
    assert note["source_url"] == "https://example.com/article"
    assert "engram ingests" in note["body"].lower()
    assert note["id"] is None
    assert note["path"].endswith(".md")


@pytest.mark.parametrize(
    "mocked_link",
    [
        lambda _req: httpx.Response(
            200, text=ARTICLE_HTML, headers={"content-type": "text/html"}
        )
    ],
    indirect=True,
)
def test_create_link_is_idempotent(
    mocked_link: None, client: TestClient, auth: dict[str, str]
) -> None:
    payload = {"url": "https://example.com/article"}
    first = client.post("/api/v1/links", headers=auth, json=payload)
    second = client.post("/api/v1/links", headers=auth, json=payload)
    assert first.status_code == 201
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]


@pytest.mark.parametrize(
    "mocked_link",
    [
        lambda _req: httpx.Response(
            200, text=ARTICLE_HTML, headers={"content-type": "text/html"}
        )
    ],
    indirect=True,
)
def test_title_override_and_tags(
    mocked_link: None, client: TestClient, auth: dict[str, str]
) -> None:
    r = client.post(
        "/api/v1/links",
        headers=auth,
        json={
            "url": "https://example.com/article",
            "title": "My Custom Title",
            "tags": ["ops", "read-later"],
        },
    )
    assert r.status_code == 201, r.text
    note = r.json()
    assert note["title"] == "My Custom Title"
    assert note["tags"] == ["ops", "read-later"]


# --- error mapping ----------------------------------------------------------


def test_blocked_host_returns_400(
    client: TestClient, auth: dict[str, str]
) -> None:
    # No override needed — the SSRF guard fires before any HTTP call. We hit
    # it directly with an IP literal so the autouse DNS stub is irrelevant.
    r = client.post(
        "/api/v1/links", headers=auth, json={"url": "http://127.0.0.1/"}
    )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "blocked_host"


@pytest.mark.parametrize(
    "mocked_link",
    [lambda _req: httpx.Response(404, text="nope")],
    indirect=True,
)
def test_unreachable_returns_422(
    mocked_link: None, client: TestClient, auth: dict[str, str]
) -> None:
    r = client.post(
        "/api/v1/links", headers=auth, json={"url": "https://example.com/x"}
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "link_unreachable"


@pytest.mark.parametrize(
    "mocked_link",
    [
        lambda _req: httpx.Response(
            200, content=b"%PDF...", headers={"content-type": "application/pdf"}
        )
    ],
    indirect=True,
)
def test_pdf_returns_415(
    mocked_link: None, client: TestClient, auth: dict[str, str]
) -> None:
    r = client.post(
        "/api/v1/links", headers=auth, json={"url": "https://example.com/f.pdf"}
    )
    assert r.status_code == 415
    assert r.json()["error"]["code"] == "unsupported_content_type"


def test_invalid_url_is_422_validation(
    client: TestClient, auth: dict[str, str]
) -> None:
    r = client.post("/api/v1/links", headers=auth, json={"url": "not-a-url"})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"


# --- auth -------------------------------------------------------------------


def test_unauthenticated_is_rejected(client: TestClient) -> None:
    r = client.post("/api/v1/links", json={"url": "https://example.com/"})
    assert r.status_code == 401
