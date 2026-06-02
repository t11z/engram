"""Runtime configuration. Core reads only the storage-relevant subset of the
``ENGRAM_*`` env contract; auth token, host, port, and CORS belong to the server.
"""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ENGRAM_", extra="ignore")

    vault_path: Path = Path("/data/vault")
    index_path: Path | None = None
    trash_retention_days: int = 30
    log_level: str = "info"
    # Path is the canonical handle; a ULID alias is optional and off by default,
    # so engram never stamps an id into notes a user may share with other tools.
    inject_id: bool = False
    # Sub-directory (relative to the vault) for notes engram creates; empty = root.
    new_note_dir: str = ""
    # Watch the vault and reconcile live (ADR-0011) while the server runs.
    watch: bool = True
    watch_debounce_seconds: float = 0.5

    @property
    def resolved_index_path(self) -> Path:
        """Index location, defaulting to ``<vault>/.engram/index.db``."""
        return self.index_path or self.vault_path / ".engram" / "index.db"

    @property
    def trash_dir(self) -> Path:
        return self.vault_path / ".trash"
