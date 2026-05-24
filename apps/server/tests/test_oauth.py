from __future__ import annotations

import base64
import hashlib
import secrets
import shutil
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient
from httpx import Response

from bartleby_server.app import create_app
from bartleby_server.config import ServerSettings

ROOT = Path(__file__).resolve().parents[3]
SAMPLE_VAULT = ROOT / "packages" / "core" / "tests" / "fixtures" / "sample-vault"
TOKEN = "test-token"
PASSWORD = "hunter2"
PUBLIC_URL = "http://localhost:8080"
REDIRECT_URI = "https://client.example.com/callback"


@pytest.fixture
def oauth_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    vault = tmp_path / "vault"
    shutil.copytree(SAMPLE_VAULT, vault)
    monkeypatch.setenv("BARTLEBY_VAULT_PATH", str(vault))
    monkeypatch.setenv("BARTLEBY_INDEX_PATH", str(tmp_path / "index.db"))
    monkeypatch.setenv("BARTLEBY_AUTH_TOKEN", TOKEN)
    monkeypatch.setenv("BARTLEBY_PUBLIC_URL", PUBLIC_URL)
    monkeypatch.setenv("BARTLEBY_OAUTH_PASSWORD", PASSWORD)
    monkeypatch.delenv("BARTLEBY_UI_DIR", raising=False)
    monkeypatch.delenv("BARTLEBY_CORS_ORIGINS", raising=False)
    return vault


@pytest.fixture
def client(oauth_env: Path) -> Iterator[TestClient]:
    with TestClient(create_app(ServerSettings())) as test_client:
        yield test_client


def _pkce() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode()
    return verifier, challenge.rstrip("=")


def _register(client: TestClient) -> dict[str, str]:
    r = client.post(
        "/register",
        json={
            "redirect_uris": [REDIRECT_URI],
            "client_name": "Test Client",
            "token_endpoint_auth_method": "client_secret_post",
        },
    )
    assert r.status_code == 201, r.text
    reg: dict[str, str] = r.json()
    return reg


def _path_and_query(location: str) -> tuple[str, dict[str, list[str]]]:
    parsed = urlparse(location)
    return parsed.path, parse_qs(parsed.query)


def _authorize(client: TestClient, client_id: str, challenge: str, *, state: str) -> str:
    r = client.get(
        "/authorize",
        params={
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": REDIRECT_URI,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "state": state,
        },
        follow_redirects=False,
    )
    assert r.status_code == 302, r.text
    path, query = _path_and_query(r.headers["location"])
    assert path == "/oauth/login"
    return query["ticket"][0]


def _login(client: TestClient, ticket: str, *, password: str) -> Response:
    return client.post(
        "/oauth/login",
        data={"ticket": ticket, "password": password},
        follow_redirects=False,
    )


def _full_flow(client: TestClient) -> dict[str, str]:
    """Register → authorize → login → token; return the token response JSON."""
    reg = _register(client)
    verifier, challenge = _pkce()
    ticket = _authorize(client, reg["client_id"], challenge, state="xyz")
    login = _login(client, ticket, password=PASSWORD)
    assert login.status_code == 302
    _, query = _path_and_query(login.headers["location"])
    assert query["state"][0] == "xyz"
    code = query["code"][0]
    r = client.post(
        "/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "client_id": reg["client_id"],
            "client_secret": reg["client_secret"],
            "code_verifier": verifier,
        },
    )
    assert r.status_code == 200, r.text
    tokens: dict[str, str] = r.json()
    return tokens


def _mcp_initialize(client: TestClient, token: str) -> int:
    headers = {
        "Authorization": f"Bearer {token}",
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
    return client.post("/mcp/", headers=headers, json=init).status_code


# -- discovery ----------------------------------------------------------------


def test_authorization_server_metadata(client: TestClient) -> None:
    r = client.get("/.well-known/oauth-authorization-server")
    assert r.status_code == 200
    body = r.json()
    assert body["issuer"].rstrip("/") == PUBLIC_URL
    assert body["authorization_endpoint"] == f"{PUBLIC_URL}/authorize"
    assert body["token_endpoint"] == f"{PUBLIC_URL}/token"
    assert body["registration_endpoint"] == f"{PUBLIC_URL}/register"
    assert body["revocation_endpoint"] == f"{PUBLIC_URL}/revoke"
    assert body["code_challenge_methods_supported"] == ["S256"]


def test_protected_resource_metadata(client: TestClient) -> None:
    r = client.get("/.well-known/oauth-protected-resource/mcp")
    assert r.status_code == 200
    body = r.json()
    assert body["resource"] == f"{PUBLIC_URL}/mcp"
    assert body["authorization_servers"] == [f"{PUBLIC_URL}/"]


def test_mcp_unauthenticated_advertises_resource_metadata(client: TestClient) -> None:
    r = client.post("/mcp/", json={"jsonrpc": "2.0", "id": 1, "method": "ping"})
    assert r.status_code == 401
    www_auth = r.headers["www-authenticate"]
    assert www_auth.startswith("Bearer")
    assert "resource_metadata=" in www_auth
    assert "/.well-known/oauth-protected-resource/mcp" in www_auth


# -- registration + full flow -------------------------------------------------


def test_dynamic_client_registration(client: TestClient) -> None:
    reg = _register(client)
    assert reg["client_id"]
    assert reg["client_secret"]
    assert REDIRECT_URI in reg["redirect_uris"]


def test_full_authorization_code_flow(client: TestClient) -> None:
    tokens = _full_flow(client)
    assert tokens["token_type"] == "Bearer"
    assert tokens["access_token"]
    assert tokens["refresh_token"]
    assert _mcp_initialize(client, tokens["access_token"]) == 200


def test_login_rejects_wrong_password(client: TestClient) -> None:
    reg = _register(client)
    _, challenge = _pkce()
    ticket = _authorize(client, reg["client_id"], challenge, state="s")
    r = _login(client, ticket, password="wrong")
    assert r.status_code == 401
    assert "location" not in r.headers


def test_token_rejects_wrong_pkce_verifier(client: TestClient) -> None:
    reg = _register(client)
    _, challenge = _pkce()
    ticket = _authorize(client, reg["client_id"], challenge, state="s")
    login = _login(client, ticket, password=PASSWORD)
    code = _path_and_query(login.headers["location"])[1]["code"][0]
    r = client.post(
        "/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "client_id": reg["client_id"],
            "client_secret": reg["client_secret"],
            "code_verifier": "not-the-right-verifier",
        },
    )
    assert r.status_code == 400
    assert r.json()["error"] == "invalid_grant"


def test_token_rejects_expired_code(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from bartleby_server.oauth import provider as provider_module

    monkeypatch.setattr(provider_module, "AUTHORIZATION_CODE_TTL_SECONDS", -10)
    reg = _register(client)
    verifier, challenge = _pkce()
    ticket = _authorize(client, reg["client_id"], challenge, state="s")
    login = _login(client, ticket, password=PASSWORD)
    code = _path_and_query(login.headers["location"])[1]["code"][0]
    r = client.post(
        "/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "client_id": reg["client_id"],
            "client_secret": reg["client_secret"],
            "code_verifier": verifier,
        },
    )
    assert r.status_code == 400
    assert r.json()["error"] == "invalid_grant"


# -- refresh + revoke ---------------------------------------------------------


def test_refresh_token_exchange(client: TestClient) -> None:
    # Run the flow inline (not via _full_flow) because we need the client_id/secret.
    reg = _register(client)
    verifier, challenge = _pkce()
    ticket = _authorize(client, reg["client_id"], challenge, state="s")
    login = _login(client, ticket, password=PASSWORD)
    code = _path_and_query(login.headers["location"])[1]["code"][0]
    first = client.post(
        "/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "client_id": reg["client_id"],
            "client_secret": reg["client_secret"],
            "code_verifier": verifier,
        },
    ).json()

    r = client.post(
        "/token",
        data={
            "grant_type": "refresh_token",
            "refresh_token": first["refresh_token"],
            "client_id": reg["client_id"],
            "client_secret": reg["client_secret"],
        },
    )
    assert r.status_code == 200, r.text
    rotated = r.json()
    assert rotated["access_token"] != first["access_token"]
    assert _mcp_initialize(client, rotated["access_token"]) == 200
    # Old (rotated-out) access token must no longer work.
    assert _mcp_initialize(client, first["access_token"]) == 401


def test_revoke_access_token(client: TestClient) -> None:
    reg = _register(client)
    verifier, challenge = _pkce()
    ticket = _authorize(client, reg["client_id"], challenge, state="s")
    login = _login(client, ticket, password=PASSWORD)
    code = _path_and_query(login.headers["location"])[1]["code"][0]
    tokens = client.post(
        "/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "client_id": reg["client_id"],
            "client_secret": reg["client_secret"],
            "code_verifier": verifier,
        },
    ).json()
    assert _mcp_initialize(client, tokens["access_token"]) == 200

    r = client.post(
        "/revoke",
        data={
            "token": tokens["access_token"],
            "client_id": reg["client_id"],
            "client_secret": reg["client_secret"],
        },
    )
    assert r.status_code == 200
    assert _mcp_initialize(client, tokens["access_token"]) == 401


# -- backwards compatibility --------------------------------------------------


def test_static_token_still_works_on_mcp(client: TestClient) -> None:
    assert _mcp_initialize(client, TOKEN) == 200


def test_static_token_still_works_on_rest(client: TestClient) -> None:
    r = client.get("/api/v1/notes", headers={"Authorization": f"Bearer {TOKEN}"})
    assert r.status_code == 200


def test_rest_still_rejects_missing_token(client: TestClient) -> None:
    r = client.get("/api/v1/notes")
    assert r.status_code == 401


# -- persistence --------------------------------------------------------------


def test_store_persists_across_reopen(tmp_path: Path) -> None:
    from mcp.shared.auth import OAuthClientInformationFull

    from bartleby_server.oauth.store import OAuthStore

    db_path = tmp_path / ".bartleby" / "oauth.db"
    store = OAuthStore(db_path)
    store.open()
    client_info = OAuthClientInformationFull(
        client_id="abc",
        client_secret="shh",
        redirect_uris=[REDIRECT_URI],
    )
    store.add_client(client_info)
    store.close()

    reopened = OAuthStore(db_path)
    reopened.open()
    loaded = reopened.get_client("abc")
    assert loaded is not None
    assert loaded.client_secret == "shh"
    reopened.close()
