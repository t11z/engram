from fastapi.testclient import TestClient


def test_healthz_is_open(client: TestClient) -> None:
    r = client.get("/healthz")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "version" in body


def test_api_requires_token(client: TestClient) -> None:
    r = client.get("/api/v1/notes")
    assert r.status_code == 401
    assert r.json() == {"error": {"code": "unauthorized", "message": "Missing bearer token."}}


def test_api_rejects_wrong_token(client: TestClient) -> None:
    r = client.get("/api/v1/notes", headers={"Authorization": "Bearer nope"})
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "forbidden"


def test_mcp_requires_token(client: TestClient) -> None:
    r = client.post("/mcp/", json={"jsonrpc": "2.0", "id": 1, "method": "ping"})
    assert r.status_code == 401
