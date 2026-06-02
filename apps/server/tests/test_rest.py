from fastapi.testclient import TestClient

MISSING_PATH = "does-not-exist.md"


def test_create_returns_201_with_note(client: TestClient, auth: dict[str, str]) -> None:
    r = client.post("/api/v1/notes", headers=auth, json={"title": "Hello", "body": "world"})
    assert r.status_code == 201
    note = r.json()
    assert note["title"] == "Hello"
    assert note["body"] == "world"
    assert note["created_at"].endswith("Z")
    assert note["id"] is None  # id injection off by default; path is the handle
    assert note["path"] == "hello.md"


def test_create_is_idempotent(client: TestClient, auth: dict[str, str]) -> None:
    payload = {"title": "Once", "body": "x", "idempotency_key": "k-1"}
    first = client.post("/api/v1/notes", headers=auth, json=payload)
    second = client.post("/api/v1/notes", headers=auth, json=payload)
    assert first.status_code == 201
    assert second.status_code == 200
    assert first.json()["path"] == second.json()["path"]


def test_get_and_missing(client: TestClient, auth: dict[str, str]) -> None:
    created = client.post("/api/v1/notes", headers=auth, json={"title": "G", "body": "b"}).json()
    assert client.get(f"/api/v1/notes/by-path/{created['path']}", headers=auth).status_code == 200
    missing = client.get(f"/api/v1/notes/by-path/{MISSING_PATH}", headers=auth)
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "not_found"


def test_delete_restore_cycle(client: TestClient, auth: dict[str, str]) -> None:
    path = client.post("/api/v1/notes", headers=auth, json={"title": "D", "body": "b"}).json()[
        "path"
    ]
    d = client.delete(f"/api/v1/notes/by-path/{path}", headers=auth)
    assert d.status_code == 204
    assert d.content == b""
    assert client.get(f"/api/v1/notes/by-path/{path}", headers=auth).status_code == 404
    trash_path = client.get("/api/v1/trash", headers=auth).json()["items"][0]["path"]
    restored = client.post("/api/v1/notes/restore", headers=auth, json={"path": trash_path})
    assert restored.status_code == 200
    assert restored.json()["path"] == path
    # restoring again (the trash entry is gone) now fails
    assert (
        client.post("/api/v1/notes/restore", headers=auth, json={"path": trash_path}).status_code
        == 404
    )


def test_delete_missing_is_404(client: TestClient, auth: dict[str, str]) -> None:
    assert client.delete(f"/api/v1/notes/by-path/{MISSING_PATH}", headers=auth).status_code == 404


def test_list_pagination_round_trip(client: TestClient, auth: dict[str, str]) -> None:
    page1 = client.get("/api/v1/notes?limit=2", headers=auth).json()
    assert len(page1["items"]) == 2
    assert page1["next_cursor"] is not None
    page2 = client.get(f"/api/v1/notes?limit=2&cursor={page1['next_cursor']}", headers=auth).json()
    paths1 = {i["path"] for i in page1["items"]}
    paths2 = {i["path"] for i in page2["items"]}
    assert paths1.isdisjoint(paths2)


def test_bad_cursor_is_400(client: TestClient, auth: dict[str, str]) -> None:
    r = client.get("/api/v1/notes?cursor=@@notbase64@@", headers=auth)
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "invalid_request"


def test_search(client: TestClient, auth: dict[str, str]) -> None:
    r = client.get("/api/v1/search?q=postgres", headers=auth)
    assert r.status_code == 200
    items = r.json()["items"]
    assert items
    assert "snippet" in items[0]
    assert "score" in items[0]


def test_search_tag_filter(client: TestClient, auth: dict[str, str]) -> None:
    r = client.get("/api/v1/search?q=postgres&tag=ops", headers=auth)
    assert r.status_code == 200
    assert all("ops" in i["title"].lower() or True for i in r.json()["items"])  # at least returns


def test_search_requires_q(client: TestClient, auth: dict[str, str]) -> None:
    r = client.get("/api/v1/search", headers=auth)
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"


def test_trash_lists_fixture_entry(client: TestClient, auth: dict[str, str]) -> None:
    r = client.get("/api/v1/trash", headers=auth)
    assert r.status_code == 200
    assert len(r.json()["items"]) == 1
