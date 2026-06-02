import shutil
from pathlib import Path
from typing import cast

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


def test_graph_structure_and_editing_tools(client: TestClient) -> None:
    a = str(mcp_server.save_note(title="A", body="a body")["path"])
    b = str(mcp_server.save_note(title="B", body=f"links to [[{a[:-3]}]]")["path"])

    assert [i["path"] for i in mcp_server.get_backlinks(path=a)] == [b]
    assert any(link["resolved_path"] == a for link in mcp_server.get_links(path=b))
    assert any(i["path"] == a for i in mcp_server.get_related(path=b))
    nodes = cast(list[dict[str, object]], mcp_server.get_graph(path=b, depth=1)["nodes"])
    assert {a, b} <= {n["path"] for n in nodes}
    assert isinstance(mcp_server.list_folders(), list)
    assert any(t["tag"] for t in mcp_server.list_tags()) or mcp_server.list_tags() == []
    assert mcp_server.get_note_by_title(title="A")["path"] == a

    assert mcp_server.update_note(path=a, body="updated")["path"] == a
    assert mcp_server.append_to_note(path=a, text="more")["path"] == a
    assert mcp_server.patch_section(path=a, heading="Log", content="e")["path"] == a


def test_resources_and_prompts_over_wire(client: TestClient, auth: dict[str, str]) -> None:
    session = _initialize(client, auth)
    templates = client.post(
        "/mcp/",
        headers=session,
        json={"jsonrpc": "2.0", "id": 5, "method": "resources/templates/list"},
    )
    assert "engram://note/" in templates.text
    prompts = client.post(
        "/mcp/", headers=session, json={"jsonrpc": "2.0", "id": 6, "method": "prompts/list"}
    )
    for name in ["summarize_note", "find_related", "daily_review"]:
        assert name in prompts.text


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
    for name in [
        "save_note",
        "search_notes",
        "read_note",
        "list_notes",
        "delete_note",
        "get_backlinks",
        "get_graph",
        "list_tags",
        "update_note",
        "patch_section",
    ]:
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
    monkeypatch.setenv("ENGRAM_WATCH", "false")
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
