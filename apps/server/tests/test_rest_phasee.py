"""Phase E REST: attachments (list + serve) and daily-note append."""

from __future__ import annotations

import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from engram_server.app import create_app
from engram_server.config import ServerSettings

ROOT = Path(__file__).resolve().parents[3]
SAMPLE_VAULT = ROOT / "packages" / "core" / "tests" / "fixtures" / "sample-vault"
TOKEN = "test-token"
PNG = b"\x89PNG\r\n\x1a\nfake-bytes"


@pytest.fixture
def attach_client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[tuple[TestClient, Path]]:
    vault = tmp_path / "vault"
    shutil.copytree(SAMPLE_VAULT, vault)
    (vault / "pic.png").write_bytes(PNG)
    monkeypatch.setenv("ENGRAM_VAULT_PATH", str(vault))
    monkeypatch.setenv("ENGRAM_INDEX_PATH", str(tmp_path / "index.db"))
    monkeypatch.setenv("ENGRAM_AUTH_TOKEN", TOKEN)
    monkeypatch.setenv("ENGRAM_WATCH", "false")
    monkeypatch.delenv("ENGRAM_UI_DIR", raising=False)
    monkeypatch.delenv("ENGRAM_CORS_ORIGINS", raising=False)
    with TestClient(create_app(ServerSettings())) as client:
        yield client, vault


def _auth() -> dict[str, str]:
    return {"Authorization": f"Bearer {TOKEN}"}


def test_list_and_serve_attachment(attach_client: tuple[TestClient, Path]) -> None:
    client, _ = attach_client
    listed = client.get("/api/v1/attachments", headers=_auth()).json()
    assert any(a["path"] == "pic.png" and a["content_type"] == "image/png" for a in listed)

    served = client.get("/api/v1/attachments/by-path/pic.png", headers=_auth())
    assert served.status_code == 200
    assert served.content == PNG
    assert served.headers["content-type"].startswith("image/png")

    missing = client.get("/api/v1/attachments/by-path/nope.png", headers=_auth())
    assert missing.status_code == 404


def test_daily_append(attach_client: tuple[TestClient, Path]) -> None:
    client, _ = attach_client
    r = client.post("/api/v1/notes/daily/append", headers=_auth(), json={"text": "- did a thing"})
    assert r.status_code == 200
    note = r.json()
    assert note["path"].endswith(".md")
    assert "did a thing" in note["body"]
    assert "ETag" in r.headers
