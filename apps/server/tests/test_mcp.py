import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from engram_server import mcp_server
from engram_server.app import create_app
from engram_server.config import ServerSettings

ROOT = Path(__file__).resolve().parents[3]
SAMPLE_VAULT = ROOT / "packages" / "core" / "tests" / "fixtures" / "sample-vault"
TOKEN = "test-token"


def test_save_and_read_note_tools(client: TestClient) -> None:
    saved = mcp_server.save_note(title="MCP note", body="hello from mcp", tags=["t"])
    assert set(saved) == {"path"}
    note = mcp_server.read_note(path=str(saved["path"]))
    assert note["title"] == "MCP note"
    assert note["body"] == "hello from mcp"
    assert note["tags"] == ["t"]


def test_search_and_list_tools(client: TestClient) -> None:
    hits = mcp_server.search_notes(query="postgres")
    assert hits
    assert {"path", "title", "snippet", "score"} <= set(hits[0])
    listed = mcp_server.list_notes(limit=5)
    assert listed
    assert {"path", "title", "tags"} <= set(listed[0])


def test_delete_note_tool(client: TestClient) -> None:
    path = str(mcp_server.save_note(title="del", body="x")["path"])
    assert mcp_server.delete_note(path=path) == {"path": path, "status": "deleted"}


def _initialize(client: TestClient, auth: dict[str, str]) -> dict[str, str]:
    headers = {
        **auth,
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
    }
    init = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "test", "version": "0"},
        },
    }
    r = client.post("/mcp/", headers=headers, json=init)
    assert r.status_code == 200
    session = {**headers, "mcp-session-id": r.headers["mcp-session-id"]}
    client.post(
        "/mcp/",
        headers=session,
        json={"jsonrpc": "2.0", "method": "notifications/initialized"},
    )
    return session


def test_tools_list_over_wire(client: TestClient, auth: dict[str, str]) -> None:
    session = _initialize(client, auth)
    r = client.post(
        "/mcp/", headers=session, json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
    )
    assert r.status_code == 200
    for name in ["save_note", "search_notes", "read_note", "list_notes", "delete_note"]:
        assert name in r.text


def test_bare_mcp_path_reaches_transport(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # claude.ai connects to the advertised resource URL `/mcp` (no trailing slash).
    # With the static UI mounted at "/" (as in production), a bare `/mcp` request
    # would otherwise fall through to StaticFiles — 404 for GET, 405 for POST — so
    # this faithfully reproduces the connector failure. NormalizeMcpPath must
    # rewrite it to `/mcp/` and serve the transport directly (no redirect).
    vault = tmp_path / "vault"
    shutil.copytree(SAMPLE_VAULT, vault)
    ui_dir = tmp_path / "ui"
    ui_dir.mkdir()
    (ui_dir / "index.html").write_text("<!doctype html>ok")
    monkeypatch.setenv("ENGRAM_VAULT_PATH", str(vault))
    monkeypatch.setenv("ENGRAM_INDEX_PATH", str(tmp_path / "index.db"))
    monkeypatch.setenv("ENGRAM_AUTH_TOKEN", TOKEN)
    monkeypatch.setenv("ENGRAM_UI_DIR", str(ui_dir))
    monkeypatch.delenv("ENGRAM_CORS_ORIGINS", raising=False)

    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
    }
    init = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "test", "version": "0"},
        },
    }
    with TestClient(create_app(ServerSettings())) as client:
        r = client.post("/mcp", headers=headers, json=init, follow_redirects=False)
    assert r.status_code == 200, f"{r.status_code}: {r.text}"
    assert "mcp-session-id" in r.headers
