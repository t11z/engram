"""Bearer-token verifier for the OAuth-protected ``/mcp`` endpoint.

Accepts two kinds of credential so existing clients keep working alongside
claude.ai: (a) the legacy static ``ENGRAM_AUTH_TOKEN`` (full scopes, no expiry),
or (b) an OAuth access token minted by :class:`EngramOAuthProvider`.
"""

from __future__ import annotations

import secrets

from mcp.server.auth.provider import AccessToken

from . import SCOPES
from .provider import EngramOAuthProvider

STATIC_CLIENT_ID = "static-bearer-token"


class EngramTokenVerifier:
    """Concrete verifier satisfying the SDK's ``TokenVerifier`` protocol."""

    def __init__(self, provider: EngramOAuthProvider, static_token: str) -> None:
        self._provider = provider
        self._static_token = static_token

    async def verify_token(self, token: str) -> AccessToken | None:
        if self._static_token and secrets.compare_digest(token, self._static_token):
            return AccessToken(
                token=token,
                client_id=STATIC_CLIENT_ID,
                scopes=list(SCOPES),
                expires_at=None,
            )
        return await self._provider.load_access_token(token)
