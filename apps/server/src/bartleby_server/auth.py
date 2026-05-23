"""Pure-ASGI bearer-token middleware.

Protects everything under ``/api`` and ``/mcp`` (covers ``/mcp`` and ``/mcp/``);
leaves ``/healthz`` and the static UI at ``/`` open. CORS preflight (OPTIONS) is
allowed through. Uses a constant-time comparison.
"""

from __future__ import annotations

import secrets

from starlette.requests import Request
from starlette.types import ASGIApp, Receive, Scope, Send

from .errors import envelope

_PROTECTED_PREFIXES = ("/api", "/mcp")


def _is_protected(path: str) -> bool:
    return any(path == prefix or path.startswith(prefix + "/") for prefix in _PROTECTED_PREFIXES)


class BearerAuthMiddleware:
    def __init__(self, app: ASGIApp, token: str) -> None:
        self.app = app
        self.token = token

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] == "OPTIONS":
            await self.app(scope, receive, send)
            return
        if not _is_protected(scope["path"]):
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
