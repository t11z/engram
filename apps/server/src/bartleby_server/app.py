"""FastAPI application factory: lifespan, auth, error handlers, and `/healthz`.

The MCP endpoint, REST routes, and static mount are added in later steps.
``create_app`` deliberately does not require an auth token (so the schema can be
exported and the app built in tests); the CLI enforces the token at serve time.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

from bartleby_core import NoteService

from . import __version__
from .auth import BearerAuthMiddleware
from .config import ServerSettings
from .errors import install_exception_handlers
from .mcp_server import mcp
from .rest import router as rest_router
from .schemas import HealthResponse
from .service import set_service


def _ui_dir() -> Path:
    override = os.environ.get("BARTLEBY_UI_DIR")
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[4] / "apps" / "web-ui" / "build"


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

    app.include_router(rest_router)

    app.mount("/mcp", mcp.streamable_http_app())

    ui_dir = _ui_dir()
    if ui_dir.is_dir():
        app.mount("/", StaticFiles(directory=ui_dir, html=True), name="ui")

    return app
