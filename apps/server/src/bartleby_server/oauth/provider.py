"""``OAuthAuthorizationServerProvider`` backed by :class:`OAuthStore`.

Implements the embedded authorization server: Dynamic Client Registration, the
authorization-code + PKCE grant, and refresh-token rotation. The actual user
consent happens on the password-gated login page (``login.py``); ``authorize``
parks the request and redirects there, and ``complete_login`` is what mints the
authorization code once the password checks out. PKCE verification, client auth,
and HTTP plumbing are handled by the SDK handlers that call into this provider.
"""

from __future__ import annotations

import secrets
import time

from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    AuthorizationParams,
    RefreshToken,
    construct_redirect_uri,
)
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken
from pydantic import AnyUrl

from . import (
    ACCESS_TOKEN_TTL_SECONDS,
    AUTHORIZATION_CODE_TTL_SECONDS,
    PENDING_AUTHORIZATION_TTL_SECONDS,
    REFRESH_TOKEN_TTL_SECONDS,
    SCOPES,
)
from .store import OAuthStore

LOGIN_PATH = "/oauth/login"


class BartlebyOAuthProvider:
    """Concrete provider satisfying ``OAuthAuthorizationServerProvider``."""

    def __init__(self, store: OAuthStore, public_url: str) -> None:
        self._store = store
        self._public_url = public_url.rstrip("/")

    # -- Dynamic Client Registration (RFC 7591) -------------------------------

    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        return self._store.get_client(client_id)

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        self._store.add_client(client_info)

    # -- authorization --------------------------------------------------------

    async def authorize(
        self, client: OAuthClientInformationFull, params: AuthorizationParams
    ) -> str:
        """Park the request and redirect the user to the password-gated login page."""
        ticket = secrets.token_urlsafe(32)
        self._store.add_pending(
            ticket,
            client_id=client.client_id or "",
            scopes=params.scopes or list(SCOPES),
            code_challenge=params.code_challenge,
            redirect_uri=str(params.redirect_uri),
            redirect_uri_provided_explicitly=params.redirect_uri_provided_explicitly,
            state=params.state,
            resource=params.resource,
            expires_at=time.time() + PENDING_AUTHORIZATION_TTL_SECONDS,
        )
        return construct_redirect_uri(f"{self._public_url}{LOGIN_PATH}", ticket=ticket)

    def complete_login(self, ticket: str) -> str | None:
        """Finalize a consented login: mint an auth code and return the client redirect.

        Returns ``None`` if the ticket is unknown or expired (already consumed by
        ``take_pending``). Called by the login route *after* the password is verified.
        """
        pending = self._store.take_pending(ticket)
        if pending is None:
            return None
        code = secrets.token_urlsafe(32)
        self._store.add_auth_code(
            AuthorizationCode(
                code=code,
                client_id=pending.client_id,
                scopes=pending.scopes,
                code_challenge=pending.code_challenge,
                redirect_uri=AnyUrl(pending.redirect_uri),
                redirect_uri_provided_explicitly=pending.redirect_uri_provided_explicitly,
                resource=pending.resource,
                expires_at=time.time() + AUTHORIZATION_CODE_TTL_SECONDS,
            )
        )
        return construct_redirect_uri(pending.redirect_uri, code=code, state=pending.state)

    async def load_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: str
    ) -> AuthorizationCode | None:
        return self._store.get_auth_code(authorization_code)

    async def exchange_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: AuthorizationCode
    ) -> OAuthToken:
        # Authorization codes are single-use (RFC 6749 §10.5).
        self._store.delete_auth_code(authorization_code.code)
        return self._issue_tokens(
            client_id=authorization_code.client_id,
            scopes=authorization_code.scopes,
            resource=authorization_code.resource,
        )

    # -- refresh --------------------------------------------------------------

    async def load_refresh_token(
        self, client: OAuthClientInformationFull, refresh_token: str
    ) -> RefreshToken | None:
        return self._store.get_refresh_token(refresh_token)

    async def exchange_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: RefreshToken,
        scopes: list[str],
    ) -> OAuthToken:
        # Rotate both tokens: drop the presented refresh token and its access token.
        paired_access = self._store.delete_refresh_token(refresh_token.token)
        if paired_access is not None:
            self._store.delete_access_token(paired_access)
        return self._issue_tokens(
            client_id=refresh_token.client_id,
            scopes=scopes or refresh_token.scopes,
            resource=None,
        )

    # -- access tokens / revocation -------------------------------------------

    async def load_access_token(self, token: str) -> AccessToken | None:
        access = self._store.get_access_token(token)
        if access is None:
            return None
        if access.expires_at is not None and access.expires_at < int(time.time()):
            self._store.delete_access_token(token)
            return None
        return access

    async def revoke_token(self, token: AccessToken | RefreshToken) -> None:
        if isinstance(token, AccessToken):
            self._store.delete_access_token(token.token)
            self._store.delete_refresh_tokens_for_access_token(token.token)
        else:
            paired_access = self._store.delete_refresh_token(token.token)
            if paired_access is not None:
                self._store.delete_access_token(paired_access)

    # -- internal -------------------------------------------------------------

    def _issue_tokens(
        self, *, client_id: str, scopes: list[str], resource: str | None
    ) -> OAuthToken:
        now = int(time.time())
        access_value = secrets.token_urlsafe(32)
        refresh_value = secrets.token_urlsafe(32)
        self._store.add_access_token(
            AccessToken(
                token=access_value,
                client_id=client_id,
                scopes=scopes,
                resource=resource,
                expires_at=now + ACCESS_TOKEN_TTL_SECONDS,
            )
        )
        self._store.add_refresh_token(
            RefreshToken(
                token=refresh_value,
                client_id=client_id,
                scopes=scopes,
                expires_at=now + REFRESH_TOKEN_TTL_SECONDS,
            ),
            access_token=access_value,
        )
        return OAuthToken(
            access_token=access_value,
            token_type="Bearer",
            expires_in=ACCESS_TOKEN_TTL_SECONDS,
            scope=" ".join(scopes),
            refresh_token=refresh_value,
        )
