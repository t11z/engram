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

    # Public HTTPS origin (no path), e.g. https://bartleby.example.com. Setting it
    # turns on the embedded OAuth authorization server so claude.ai can connect as
    # a Custom Connector; it also becomes the OAuth issuer / resource identifier.
    public_url: str = ""
    # Login-gate password for the OAuth consent page. Required when public_url is set.
    oauth_password: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def oauth_enabled(self) -> bool:
        return bool(self.public_url)
