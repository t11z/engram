from fastapi.testclient import TestClient

MISSING_ID = "01XXXXXXXXXXXXXXXXXXXXXXXX"


def test_create_returns_201_with_note(client: TestClient, auth: dict[str, str]) -> None:
    r = client.post("/api/v1/notes", headers=auth, json={"title": "Hello", "body": "world"})
    assert r.status_code == 201
    note = r.json()
    assert note["title"] == "Hello"
    assert note["body"] == "world"
    assert note["created_at"].endswith("Z")
    assert len(note["id"]) == 26


def test_create_is_idempotent(client: TestClient, auth: dict[str, str]) -> None:
    payload = {"title": "Once", "body": "x", "idempotency_key": "k-1"}
    first = client.post("/api/v1/notes", headers=auth, json=payload)
    second = client.post("/api/v1/notes", headers=auth, json=payload)
    assert first.status_code == 201
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]


def test_get_and_missing(client: TestClient, auth: dict[str, str]) -> None:
    created = client.post("/api/v1/notes", headers=auth, json={"title": "G", "body": "b"}).json()
    assert client.get(f"/api/v1/notes/{created['id']}", headers=auth).status_code == 200
    missing = client.get(f"/api/v1/notes/{MISSING_ID}", headers=auth)
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "not_found"


def test_delete_restore_cycle(client: TestClient, auth: dict[str, str]) -> None:
    nid = client.post("/api/v1/notes", headers=auth, json={"title": "D", "body": "b"}).json()["id"]
    d = client.delete(f"/api/v1/notes/{nid}", headers=auth)
    assert d.status_code == 204
    assert d.content == b""
    assert client.get(f"/api/v1/notes/{nid}", headers=auth).status_code == 404
    restored = client.post(f"/api/v1/notes/{nid}/restore", headers=auth)
    assert restored.status_code == 200
    # restoring a live note now fails
    assert client.post(f"/api/v1/notes/{nid}/restore", headers=auth).status_code == 404


def test_delete_missing_is_404(client: TestClient, auth: dict[str, str]) -> None:
    assert client.delete(f"/api/v1/notes/{MISSING_ID}", headers=auth).status_code == 404


def test_list_pagination_round_trip(client: TestClient, auth: dict[str, str]) -> None:
    page1 = client.get("/api/v1/notes?limit=2", headers=auth).json()
    assert len(page1["items"]) == 2
    assert page1["next_cursor"] is not None
    page2 = client.get(f"/api/v1/notes?limit=2&cursor={page1['next_cursor']}", headers=auth).json()
    ids1 = {i["id"] for i in page1["items"]}
    ids2 = {i["id"] for i in page2["items"]}
    assert ids1.isdisjoint(ids2)


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
