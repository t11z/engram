"""Runtime configuration. Core reads only the storage-relevant subset of the
``BARTLEBY_*`` env contract; auth token, host, port, and CORS belong to the server.
"""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BARTLEBY_", extra="ignore")

    vault_path: Path = Path("/data/vault")
    index_path: Path | None = None
    trash_retention_days: int = 30
    log_level: str = "info"

    @property
    def resolved_index_path(self) -> Path:
        """Index location, defaulting to ``<vault>/.bartleby/index.db``."""
        return self.index_path or self.vault_path / ".bartleby" / "index.db"

    @property
    def trash_dir(self) -> Path:
        return self.vault_path / ".trash"
