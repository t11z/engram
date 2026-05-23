from fastapi.testclient import TestClient

from bartleby_server import mcp_server


def test_save_and_read_note_tools(client: TestClient) -> None:
    saved = mcp_server.save_note(title="MCP note", body="hello from mcp", tags=["t"])
    assert set(saved) == {"id"}
    note = mcp_server.read_note(id=saved["id"])
    assert note["title"] == "MCP note"
    assert note["body"] == "hello from mcp"
    assert note["tags"] == ["t"]


def test_search_and_list_tools(client: TestClient) -> None:
    hits = mcp_server.search_notes(query="postgres")
    assert hits
    assert {"id", "title", "snippet", "score"} <= set(hits[0])
    listed = mcp_server.list_notes(limit=5)
    assert listed
    assert {"id", "title", "tags"} <= set(listed[0])


def test_delete_note_tool(client: TestClient) -> None:
    nid = mcp_server.save_note(title="del", body="x")["id"]
    assert mcp_server.delete_note(id=nid) == {"id": nid, "status": "deleted"}


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
