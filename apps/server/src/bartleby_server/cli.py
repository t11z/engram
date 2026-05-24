"""``bartleby`` entry point: serve the app with uvicorn."""

from __future__ import annotations

import sys

import uvicorn

from .app import create_app
from .config import ServerSettings


def main() -> None:
    settings = ServerSettings()
    if not settings.auth_token:
        sys.stderr.write(
            "BARTLEBY_AUTH_TOKEN is required. Generate one with: openssl rand -hex 32\n"
        )
        raise SystemExit(2)
    if settings.public_url and not settings.oauth_password:
        sys.stderr.write(
            "BARTLEBY_OAUTH_PASSWORD is required when BARTLEBY_PUBLIC_URL is set "
            "(it gates the OAuth login page). Generate one with: openssl rand -hex 32\n"
        )
        raise SystemExit(2)
    app = create_app(settings)
    uvicorn.run(app, host=settings.host, port=settings.port)
