"""FastAPI application factory: lifespan, auth, error handlers, and `/healthz`.

The MCP endpoint, REST routes, and static mount are added in later steps.
``create_app`` deliberately does not require an auth token (so the schema can be
exported and the app built in tests); the CLI enforces the token at serve time.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from bartleby_core import NoteService

from . import __version__
from .auth import BearerAuthMiddleware
from .config import ServerSettings
from .errors import install_exception_handlers
from .mcp_server import mcp
from .schemas import HealthResponse
from .service import set_service


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    service = NoteService.from_env()
    service.startup()
    set_service(service)
    try:
        async with mcp.session_manager.run():
            yield
    finally:
        set_service(None)
        service.close()


def create_app(settings: ServerSettings | None = None) -> FastAPI:
    settings = settings or ServerSettings()
    app = FastAPI(title="Bartleby", version=__version__, lifespan=_lifespan)
    install_exception_handlers(app)

    app.add_middleware(BearerAuthMiddleware, token=settings.auth_token)
    if settings.cors_origin_list:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origin_list,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @app.get("/healthz", response_model=HealthResponse)
    async def healthz() -> HealthResponse:
        return HealthResponse(status="ok", version=__version__)

    app.mount("/mcp", mcp.streamable_http_app())

    return app
