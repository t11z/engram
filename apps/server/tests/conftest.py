from __future__ import annotations

import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from bartleby_server.app import create_app
from bartleby_server.config import ServerSettings

ROOT = Path(__file__).resolve().parents[3]
SAMPLE_VAULT = ROOT / "packages" / "core" / "tests" / "fixtures" / "sample-vault"
TOKEN = "test-token"


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    vault = tmp_path / "vault"
    shutil.copytree(SAMPLE_VAULT, vault)
    monkeypatch.setenv("BARTLEBY_VAULT_PATH", str(vault))
    monkeypatch.setenv("BARTLEBY_INDEX_PATH", str(tmp_path / "index.db"))
    monkeypatch.setenv("BARTLEBY_AUTH_TOKEN", TOKEN)
    monkeypatch.delenv("BARTLEBY_UI_DIR", raising=False)
    monkeypatch.delenv("BARTLEBY_CORS_ORIGINS", raising=False)
    with TestClient(create_app(ServerSettings())) as test_client:
        yield test_client


@pytest.fixture
def auth() -> dict[str, str]:
    return {"Authorization": f"Bearer {TOKEN}"}
