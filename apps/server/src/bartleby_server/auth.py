"""Pure-ASGI bearer-token middleware.

By default protects everything under ``/api`` and ``/mcp`` (covers ``/mcp`` and
``/mcp/``); leaves ``/healthz`` and the static UI at ``/`` open. CORS preflight
(OPTIONS) is allowed through. Uses a constant-time comparison.

When the embedded OAuth server is enabled, ``/mcp`` is protected by the SDK
middleware chain instead, so the app narrows this middleware's prefixes to
``/api`` alone (see ``create_app``).
"""

from __future__ import annotations

import secrets
from collections.abc import Sequence

from starlette.requests import Request
from starlette.types import ASGIApp, Receive, Scope, Send

from .errors import envelope

_DEFAULT_PROTECTED_PREFIXES = ("/api", "/mcp")


class BearerAuthMiddleware:
    def __init__(
        self, app: ASGIApp, token: str, protected_prefixes: Sequence[str] | None = None
    ) -> None:
        self.app = app
        self.token = token
        self.protected_prefixes = tuple(
            protected_prefixes if protected_prefixes is not None else _DEFAULT_PROTECTED_PREFIXES
        )

    def _is_protected(self, path: str) -> bool:
        return any(
            path == prefix or path.startswith(prefix + "/") for prefix in self.protected_prefixes
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] == "OPTIONS":
            await self.app(scope, receive, send)
            return
        if not self._is_protected(scope["path"]):
            await self.app(scope, receive, send)
            return

        header = Request(scope).headers.get("authorization", "")
        if not header:
            await envelope(401, "unauthorized", "Missing bearer token.")(scope, receive, send)
            return
        scheme, _, presented = header.partition(" ")
        if scheme.lower() != "bearer" or not secrets.compare_digest(presented, self.token):
            await envelope(403, "forbidden", "Invalid bearer token.")(scope, receive, send)
            return
        await self.app(scope, receive, send)
