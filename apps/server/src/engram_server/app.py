"""FastAPI application factory: lifespan, auth, error handlers, and `/healthz`.

The MCP endpoint, REST routes, and static mount are added here. ``create_app``
deliberately does not require an auth token (so the schema can be exported and the
app built in tests); the CLI enforces the token at serve time.

When ``ENGRAM_PUBLIC_URL`` is set, the embedded OAuth authorization server is
wired in (see ``engram_server.oauth``): OAuth metadata/endpoints are mounted at
the app root and ``/mcp`` is protected by the SDK middleware chain, which accepts
both OAuth tokens and the legacy static bearer token.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from mcp.server.auth.middleware.auth_context import AuthContextMiddleware
from mcp.server.auth.middleware.bearer_auth import BearerAuthBackend, RequireAuthMiddleware
from mcp.server.auth.routes import (
    build_resource_metadata_url,
    create_auth_routes,
    create_protected_resource_routes,
)
from mcp.server.auth.settings import ClientRegistrationOptions, RevocationOptions
from mcp.server.fastmcp import FastMCP
from pydantic import AnyHttpUrl
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles
from starlette.types import ASGIApp, Receive, Scope, Send

from engram_core import NoteService
from engram_core import Settings as CoreSettings

from . import __version__
from .auth import BearerAuthMiddleware
from .config import ServerSettings
from .errors import install_exception_handlers
from .mcp_server import build_mcp
from .oauth import SCOPES
from .oauth.login import create_login_routes
from .oauth.provider import EngramOAuthProvider
from .oauth.store import OAuthStore
from .oauth.verifier import EngramTokenVerifier
from .rest import router as rest_router
from .schemas import HealthResponse
from .service import set_service


def _ui_dir() -> Path:
    override = os.environ.get("ENGRAM_UI_DIR")
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[4] / "apps" / "web-ui" / "build"


class NormalizeMcpPath:
    """Serve the MCP transport at the bare ``/mcp`` path, not only ``/mcp/``.

    The OAuth protected-resource metadata advertises ``<public_url>/mcp`` (no
    trailing slash) as the MCP resource, and that is the URL claude.ai connects
    to. But the transport is ``app.mount``ed at ``/mcp``, and Starlette only
    routes a mounted app for ``/mcp/...`` — a request to the bare ``/mcp`` falls
    through to the static-UI mount at ``/`` instead (``GET`` → 404, ``POST`` →
    405, since ``StaticFiles`` serves neither). claude.ai therefore can't reach
    the transport after authorizing.

    Rewrite the bare path to ``/mcp/`` before routing so the request hits the
    mount. Doing it here (rather than returning a redirect) means the server
    actually serves the resource URL it advertises and does not depend on the
    client following a redirect on a POST body.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope.get("path") == "/mcp":
            scope = dict(scope)
            scope["path"] = "/mcp/"
            if scope.get("raw_path") == b"/mcp":
                scope["raw_path"] = b"/mcp/"
        await self.app(scope, receive, send)


def _install_oauth(
    app: FastAPI,
    settings: ServerSettings,
    provider: EngramOAuthProvider,
    verifier: EngramTokenVerifier,
    mcp: FastMCP,
) -> None:
    """Mount OAuth metadata/endpoints at the app root and protect ``/mcp``.

    Metadata and endpoints (``/.well-known/...``, ``/authorize``, ``/token``,
    ``/register``, ``/revoke``, ``/oauth/login``) must live at the root because that
    is where claude.ai looks for them — hence we register the SDK route factories
    directly rather than mounting FastMCP's own (which would sit under ``/mcp``).
    """
    issuer_url = AnyHttpUrl(settings.public_url)
    resource_url = AnyHttpUrl(settings.public_url.rstrip("/") + "/mcp")

    auth_routes = create_auth_routes(
        provider=provider,
        issuer_url=issuer_url,
        client_registration_options=ClientRegistrationOptions(
            enabled=True,
            valid_scopes=list(SCOPES),
            default_scopes=list(SCOPES),
        ),
        revocation_options=RevocationOptions(enabled=True),
    )
    prm_routes = create_protected_resource_routes(
        resource_url=resource_url,
        authorization_servers=[issuer_url],
        scopes_supported=list(SCOPES),
    )
    login_routes = create_login_routes(provider, settings.oauth_password)
    app.router.routes.extend([*auth_routes, *prm_routes, *login_routes])

    # Protect /mcp with the same chain FastMCP composes internally: authenticate the
    # bearer token, expose it in the request context, then require a valid token. The
    # resource-metadata URL drives the WWW-Authenticate header claude.ai follows.
    resource_metadata_url = build_resource_metadata_url(resource_url)
    mcp_app = AuthenticationMiddleware(
        AuthContextMiddleware(
            RequireAuthMiddleware(mcp.streamable_http_app(), [], resource_metadata_url)
        ),
        backend=BearerAuthBackend(verifier),
    )
    app.mount("/mcp", mcp_app)


def create_app(settings: ServerSettings | None = None) -> FastAPI:
    settings = settings or ServerSettings()
    mcp = build_mcp()

    oauth_store: OAuthStore | None = None
    oauth_provider: EngramOAuthProvider | None = None
    oauth_verifier: EngramTokenVerifier | None = None
    if settings.oauth_enabled:
        db_path = CoreSettings().vault_path / ".engram" / "oauth.db"
        oauth_store = OAuthStore(db_path)
        oauth_provider = EngramOAuthProvider(oauth_store, settings.public_url)
        oauth_verifier = EngramTokenVerifier(oauth_provider, settings.auth_token)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        service = NoteService.from_env()
        service.startup()
        set_service(service)
        if oauth_store is not None:
            oauth_store.open()
        try:
            async with mcp.session_manager.run():
                yield
        finally:
            set_service(None)
            service.close()
            if oauth_store is not None:
                oauth_store.close()

    app = FastAPI(title="Engram", version=__version__, lifespan=lifespan)
    install_exception_handlers(app)

    # With OAuth on, /mcp is guarded by the SDK chain, so this middleware narrows to
    # /api; without OAuth it keeps protecting both /api and /mcp as before.
    protected_prefixes = ("/api",) if settings.oauth_enabled else None
    app.add_middleware(
        BearerAuthMiddleware, token=settings.auth_token, protected_prefixes=protected_prefixes
    )
    if settings.cors_origin_list:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origin_list,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    # Outermost: normalise bare `/mcp` to `/mcp/` so claude.ai reaches the mounted
    # transport (the resource URL is advertised without a trailing slash).
    app.add_middleware(NormalizeMcpPath)

    @app.get("/healthz", response_model=HealthResponse)
    async def healthz() -> HealthResponse:
        return HealthResponse(status="ok", version=__version__)

    app.include_router(rest_router)

    if oauth_provider is not None and oauth_verifier is not None:
        _install_oauth(app, settings, oauth_provider, oauth_verifier, mcp)
    else:
        app.mount("/mcp", mcp.streamable_http_app())

    ui_dir = _ui_dir()
    if ui_dir.is_dir():
        app.mount("/", StaticFiles(directory=ui_dir, html=True), name="ui")

    return app
