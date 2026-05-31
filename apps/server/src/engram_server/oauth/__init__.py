"""Embedded OAuth 2.1 authorization server for the MCP endpoint.

Lets claude.ai (and any spec-compliant MCP client) connect to ``/mcp`` via the
OAuth authorization-code + PKCE flow with Dynamic Client Registration, while the
legacy static ``ENGRAM_AUTH_TOKEN`` keeps working. Built entirely on the OAuth
primitives shipped in the ``mcp`` SDK plus stdlib ``sqlite3`` — no new dependency.

Only active when ``ENGRAM_PUBLIC_URL`` is configured; otherwise the server
behaves exactly as before.
"""

from __future__ import annotations

# Token / code lifetimes. Kept as constants (no extra env vars) per the design.
ACCESS_TOKEN_TTL_SECONDS = 60 * 60  # 1 hour
REFRESH_TOKEN_TTL_SECONDS = 60 * 60 * 24 * 30  # 30 days
AUTHORIZATION_CODE_TTL_SECONDS = 5 * 60  # 5 minutes
PENDING_AUTHORIZATION_TTL_SECONDS = 10 * 60  # 10 minutes

# Single scope granted to every Engram token. The MCP client need not request it.
SCOPES = ["engram"]

__all__ = [
    "ACCESS_TOKEN_TTL_SECONDS",
    "AUTHORIZATION_CODE_TTL_SECONDS",
    "PENDING_AUTHORIZATION_TTL_SECONDS",
    "REFRESH_TOKEN_TTL_SECONDS",
    "SCOPES",
]
