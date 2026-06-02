"""REST endpoints added in Phase B: editing (If-Match) and graph/structure reads."""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient


def _create(
    client: TestClient, auth: dict[str, str], title: str = "N", body: str = "b"
) -> dict[str, Any]:
    r = client.post("/api/v1/notes", headers=auth, json={"title": title, "body": body})
    assert r.status_code == 201
    data: dict[str, Any] = r.json()
    return data


def _etag(client: TestClient, auth: dict[str, str], path: str) -> str:
    return client.get(f"/api/v1/notes/by-path/{path}", headers=auth).headers["ETag"]


def test_update_requires_if_match(client: TestClient, auth: dict[str, str]) -> None:
    note = _create(client, auth)
    r = client.put(f"/api/v1/notes/by-path/{note['path']}", headers=auth, json={"body": "x"})
    assert r.status_code == 428
    assert r.json()["error"]["code"] == "precondition_required"


def test_update_with_matching_if_match(client: TestClient, auth: dict[str, str]) -> None:
    note = _create(client, auth, body="orig")
    etag = _etag(client, auth, note["path"])
    r = client.put(
        f"/api/v1/notes/by-path/{note['path']}",
        headers={**auth, "If-Match": etag},
        json={"body": "updated"},
    )
    assert r.status_code == 200
    assert r.json()["body"] == "updated"
    assert r.headers["ETag"] != etag


def test_update_stale_if_match_conflicts(client: TestClient, auth: dict[str, str]) -> None:
    note = _create(client, auth, body="orig")
    etag = _etag(client, auth, note["path"])
    client.put(
        f"/api/v1/notes/by-path/{note['path']}",
        headers={**auth, "If-Match": etag},
        json={"body": "first"},
    )
    r = client.put(
        f"/api/v1/notes/by-path/{note['path']}",
        headers={**auth, "If-Match": etag},  # now stale
        json={"body": "second"},
    )
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "conflict"


def test_append_and_patch_section(client: TestClient, auth: dict[str, str]) -> None:
    note = _create(client, auth, body="alpha")
    r = client.post(
        "/api/v1/notes/append", headers=auth, json={"path": note["path"], "text": "beta"}
    )
    assert r.status_code == 200
    assert r.json()["body"].rstrip().endswith("beta")
    r = client.post(
        "/api/v1/notes/patch-section",
        headers=auth,
        json={"path": note["path"], "heading": "Log", "content": "entry"},
    )
    assert r.status_code == 200
    assert "## Log" in r.json()["body"]


def test_graph_and_structure_reads(client: TestClient, auth: dict[str, str]) -> None:
    a = _create(client, auth, "A", "a body")
    b = _create(client, auth, "B", f"links to [[{a['path'][:-3]}]]")

    backlinks = client.get("/api/v1/backlinks", headers=auth, params={"path": a["path"]}).json()
    assert any(i["path"] == b["path"] for i in backlinks["items"])

    related = client.get("/api/v1/related", headers=auth, params={"path": b["path"]}).json()
    assert any(i["path"] == a["path"] for i in related["items"])

    links = client.get("/api/v1/links", headers=auth, params={"path": b["path"]}).json()
    assert any(link["resolved_path"] == a["path"] for link in links)

    graph = client.get(
        "/api/v1/graph", headers=auth, params={"path": b["path"], "depth": 1}
    ).json()
    assert {a["path"], b["path"]} <= {n["path"] for n in graph["nodes"]}

    assert isinstance(client.get("/api/v1/folders", headers=auth).json(), list)
    assert isinstance(client.get("/api/v1/tags", headers=auth).json(), list)


def test_get_by_title(client: TestClient, auth: dict[str, str]) -> None:
    note = _create(client, auth, "Special Title", "x")
    r = client.get("/api/v1/notes/by-title", headers=auth, params={"title": "Special Title"})
    assert r.status_code == 200
    assert r.json()["path"] == note["path"]
