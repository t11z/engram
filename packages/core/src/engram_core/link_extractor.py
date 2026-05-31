"""Fetch a public URL, validate the response, and extract its article body as
Markdown. No vault writes here — :class:`engram_core.service.LinkService`
composes this with :class:`NoteService.create` to produce a stored note.

This module is the only place in the codebase that makes outbound HTTP calls.
The guard contract is intentionally strict (see :func:`_assert_public_host`):

- http(s) schemes only, no userinfo;
- the host must resolve to a public unicast address (no private, loopback,
  link-local, multicast, reserved, or unspecified ranges);
- the guard is re-applied after every redirect.
"""

from __future__ import annotations

import ipaddress
import socket
from collections.abc import Iterable
from dataclasses import dataclass, field
from urllib.parse import urlparse

import httpx
import trafilatura
from bs4 import BeautifulSoup
from markdownify import markdownify

from .errors import (
    BlockedHost,
    LinkExtractionFailed,
    LinkTimeout,
    LinkTooLarge,
    LinkUnreachable,
    UnsupportedContentType,
)

_DEFAULT_USER_AGENT = "Engram/0.1 (+link-importer)"
_DEFAULT_ALLOWED_TYPES: frozenset[str] = frozenset({"text/html", "application/xhtml+xml"})


@dataclass(frozen=True)
class LinkFetchSettings:
    timeout: float = 10.0
    max_bytes: int = 5_000_000
    max_redirects: int = 5
    user_agent: str = _DEFAULT_USER_AGENT
    allowed_content_types: frozenset[str] = field(default_factory=lambda: _DEFAULT_ALLOWED_TYPES)
    # Optional ``httpx`` transport, used by tests to inject ``MockTransport``.
    # Production code leaves this ``None``; httpx then picks the default.
    transport: httpx.AsyncBaseTransport | None = None


@dataclass(frozen=True)
class ExtractedArticle:
    title: str
    markdown: str
    final_url: str


async def fetch_and_extract(
    url: str, *, settings: LinkFetchSettings | None = None
) -> ExtractedArticle:
    """Fetch ``url``, follow redirects manually with SSRF checks at every hop,
    and return the extracted article as Markdown.
    """
    cfg = settings or LinkFetchSettings()
    current = url
    html_text: str | None = None
    async with httpx.AsyncClient(
        timeout=cfg.timeout,
        follow_redirects=False,
        headers={"User-Agent": cfg.user_agent},
        transport=cfg.transport,
    ) as client:
        for _ in range(cfg.max_redirects + 1):
            _assert_public_host(current)
            result = await _fetch_once(
                client,
                current,
                max_bytes=cfg.max_bytes,
                allowed_types=cfg.allowed_content_types,
            )
            if isinstance(result, _Redirect):
                current = result.target
                continue
            html_text = result.html
            current = result.final_url
            break
        else:
            raise LinkUnreachable(f"too many redirects from {url!r}")

    assert html_text is not None  # loop guarantees this
    title, markdown = _extract_article(html_text, current)
    return ExtractedArticle(title=title, markdown=markdown, final_url=current)


# --- URL validation & SSRF guard -------------------------------------------


def _assert_public_host(url: str) -> None:
    """Reject non-http(s) schemes, userinfo, and hosts that resolve to any
    non-public IP. Raises :class:`BlockedHost` on rejection.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise BlockedHost(f"unsupported URL scheme {parsed.scheme!r}")
    if parsed.username or parsed.password:
        raise BlockedHost("URLs with embedded credentials are not allowed")
    host = parsed.hostname
    if not host:
        raise BlockedHost(f"URL has no host: {url!r}")

    # If the literal already parses as an IP, check it directly. Otherwise
    # resolve via getaddrinfo and check every returned address.
    try:
        addrs: Iterable[str] = [str(ipaddress.ip_address(host))]
    except ValueError:
        try:
            infos = socket.getaddrinfo(host, None)
        except OSError as exc:
            raise BlockedHost(f"could not resolve host {host!r}: {exc}") from exc
        addrs = {str(info[4][0]) for info in infos}

    for raw in addrs:
        ip = ipaddress.ip_address(raw)
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            raise BlockedHost(f"host {host!r} resolves to non-public address {raw}")


# --- HTTP fetch -------------------------------------------------------------


@dataclass(frozen=True)
class _Redirect:
    target: str


@dataclass(frozen=True)
class _Body:
    html: str
    final_url: str


async def _fetch_once(
    client: httpx.AsyncClient,
    url: str,
    *,
    max_bytes: int,
    allowed_types: frozenset[str],
) -> _Redirect | _Body:
    """Fetch one URL with redirect-following disabled. Returns a ``_Redirect``
    when the server returns 3xx (so the caller can re-check SSRF), or a
    ``_Body`` for a successful response.
    """
    try:
        async with client.stream("GET", url) as response:
            if response.is_redirect:
                location = response.headers.get("location")
                if not location:
                    raise LinkUnreachable(f"redirect from {url!r} has no Location header")
                return _Redirect(target=str(httpx.URL(url).join(location)))
            if response.status_code >= 400:
                raise LinkUnreachable(f"{url!r} returned HTTP {response.status_code}")

            ct = response.headers.get("content-type", "").split(";")[0].strip().lower()
            if ct and ct not in allowed_types:
                raise UnsupportedContentType(
                    f"unsupported content type {ct!r} for {url!r}"
                )

            body = bytearray()
            async for chunk in response.aiter_bytes():
                body.extend(chunk)
                if len(body) > max_bytes:
                    raise LinkTooLarge(f"{url!r} exceeded {max_bytes} bytes")
            encoding = response.encoding or "utf-8"
            html = bytes(body).decode(encoding, errors="replace")
            return _Body(html=html, final_url=str(response.url))
    except httpx.TimeoutException as exc:
        raise LinkTimeout(f"timeout fetching {url!r}") from exc
    except httpx.RequestError as exc:
        raise LinkUnreachable(f"failed to fetch {url!r}: {exc}") from exc


# --- Extraction -------------------------------------------------------------


def _extract_article(html: str, url: str) -> tuple[str, str]:
    """Return ``(title, markdown)``. Raises :class:`LinkExtractionFailed` when
    the page yields no usable body even after the markdownify fallback.
    """
    soup = BeautifulSoup(html, "html.parser")
    title = _extract_title(soup, url)
    markdown = trafilatura.extract(
        html,
        output_format="markdown",
        url=url,
        include_links=True,
        include_images=False,
        with_metadata=False,
    )
    if not markdown or not markdown.strip():
        body = soup.body
        markdown = markdownify(str(body) if body else html)
    if not markdown or not markdown.strip():
        raise LinkExtractionFailed(f"could not extract article from {url!r}")
    return title, markdown.strip()


def _extract_title(soup: BeautifulSoup, url: str) -> str:
    og = soup.find("meta", attrs={"property": "og:title"})
    if og is not None:
        content = og.get("content")
        if isinstance(content, str) and content.strip():
            return content.strip()
    title_tag = soup.find("title")
    if title_tag is not None and title_tag.string and title_tag.string.strip():
        return title_tag.string.strip()
    h1 = soup.find("h1")
    if h1 is not None:
        text = h1.get_text(strip=True)
        if text:
            return text
    parsed = urlparse(url)
    fallback = f"{parsed.hostname or 'link'}{parsed.path}".rstrip("/")
    return fallback or url
