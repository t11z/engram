"""Server-only configuration. Core reads its own storage settings; the server
owns auth, bind address, and CORS. Both share the ``BARTLEBY_`` env prefix.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class ServerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BARTLEBY_", extra="ignore")

    auth_token: str = ""
    host: str = "0.0.0.0"
    port: int = 8080
    cors_origins: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
