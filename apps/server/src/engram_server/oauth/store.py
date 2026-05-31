"""Persistent SQLite storage for the embedded OAuth server.

Lives at ``<vault>/.engram/oauth.db`` — separate from the rebuildable FTS index,
because clients and tokens are not reconstructable and must survive restarts so
claude.ai stays connected. All access goes through this class; it serializes
writes with a lock and is safe to call from Starlette's threadpool.
"""

from __future__ import annotations

import sqlite3
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from mcp.server.auth.provider import AccessToken, AuthorizationCode, RefreshToken
from mcp.shared.auth import OAuthClientInformationFull
from pydantic import AnyUrl


@dataclass
class PendingAuthorization:
    """An authorization request parked while the user completes the login page."""

    client_id: str
    scopes: list[str]
    code_challenge: str
    redirect_uri: str
    redirect_uri_provided_explicitly: bool
    state: str | None
    resource: str | None

_SCHEMA = """
CREATE TABLE IF NOT EXISTS clients (
    client_id  TEXT PRIMARY KEY,
    data       TEXT NOT NULL,
    created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS pending_authorizations (
    ticket                          TEXT PRIMARY KEY,
    client_id                       TEXT NOT NULL,
    scopes                          TEXT NOT NULL,
    code_challenge                  TEXT NOT NULL,
    redirect_uri                    TEXT NOT NULL,
    redirect_uri_provided_explicitly INTEGER NOT NULL,
    state                           TEXT,
    resource                        TEXT,
    expires_at                      REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS auth_codes (
    code                            TEXT PRIMARY KEY,
    client_id                       TEXT NOT NULL,
    scopes                          TEXT NOT NULL,
    code_challenge                  TEXT NOT NULL,
    redirect_uri                    TEXT NOT NULL,
    redirect_uri_provided_explicitly INTEGER NOT NULL,
    resource                        TEXT,
    expires_at                      REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS access_tokens (
    token      TEXT PRIMARY KEY,
    client_id  TEXT NOT NULL,
    scopes     TEXT NOT NULL,
    resource   TEXT,
    expires_at INTEGER
);
CREATE TABLE IF NOT EXISTS refresh_tokens (
    token        TEXT PRIMARY KEY,
    client_id    TEXT NOT NULL,
    scopes       TEXT NOT NULL,
    access_token TEXT,
    expires_at   INTEGER
);
"""


def _join(scopes: list[str]) -> str:
    return " ".join(scopes)


def _split(scopes: str) -> list[str]:
    return scopes.split() if scopes else []


class OAuthStore:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._lock = threading.Lock()
        self._conn: sqlite3.Connection | None = None

    def open(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.executescript(_SCHEMA)
        conn.commit()
        self._conn = conn

    def close(self) -> None:
        with self._lock:
            if self._conn is not None:
                self._conn.close()
                self._conn = None

    @property
    def _db(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError("OAuthStore is not open; the app lifespan has not run.")
        return self._conn

    # -- clients (Dynamic Client Registration) --------------------------------

    def add_client(self, client: OAuthClientInformationFull) -> None:
        with self._lock:
            self._db.execute(
                "INSERT OR REPLACE INTO clients (client_id, data, created_at) VALUES (?, ?, ?)",
                (client.client_id, client.model_dump_json(), int(time.time())),
            )
            self._db.commit()

    def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        with self._lock:
            row = self._db.execute(
                "SELECT data FROM clients WHERE client_id = ?", (client_id,)
            ).fetchone()
        if row is None:
            return None
        return OAuthClientInformationFull.model_validate_json(row["data"])

    # -- pending authorizations (between /authorize and the login page) -------

    def add_pending(
        self,
        ticket: str,
        *,
        client_id: str,
        scopes: list[str],
        code_challenge: str,
        redirect_uri: str,
        redirect_uri_provided_explicitly: bool,
        state: str | None,
        resource: str | None,
        expires_at: float,
    ) -> None:
        with self._lock:
            self._db.execute(
                "INSERT INTO pending_authorizations (ticket, client_id, scopes, code_challenge, "
                "redirect_uri, redirect_uri_provided_explicitly, state, resource, expires_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    ticket,
                    client_id,
                    _join(scopes),
                    code_challenge,
                    redirect_uri,
                    int(redirect_uri_provided_explicitly),
                    state,
                    resource,
                    expires_at,
                ),
            )
            self._db.commit()

    def take_pending(self, ticket: str) -> PendingAuthorization | None:
        """Atomically read and delete a pending authorization; None if missing/expired."""
        with self._lock:
            row = self._db.execute(
                "SELECT * FROM pending_authorizations WHERE ticket = ?", (ticket,)
            ).fetchone()
            if row is not None:
                self._db.execute(
                    "DELETE FROM pending_authorizations WHERE ticket = ?", (ticket,)
                )
                self._db.commit()
        if row is None or row["expires_at"] < time.time():
            return None
        return PendingAuthorization(
            client_id=row["client_id"],
            scopes=_split(row["scopes"]),
            code_challenge=row["code_challenge"],
            redirect_uri=row["redirect_uri"],
            redirect_uri_provided_explicitly=bool(row["redirect_uri_provided_explicitly"]),
            state=row["state"],
            resource=row["resource"],
        )

    # -- authorization codes --------------------------------------------------

    def add_auth_code(self, code: AuthorizationCode) -> None:
        with self._lock:
            self._db.execute(
                "INSERT INTO auth_codes (code, client_id, scopes, code_challenge, redirect_uri, "
                "redirect_uri_provided_explicitly, resource, expires_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    code.code,
                    code.client_id,
                    _join(code.scopes),
                    code.code_challenge,
                    str(code.redirect_uri),
                    int(code.redirect_uri_provided_explicitly),
                    code.resource,
                    code.expires_at,
                ),
            )
            self._db.commit()

    def get_auth_code(self, code: str) -> AuthorizationCode | None:
        with self._lock:
            row = self._db.execute(
                "SELECT * FROM auth_codes WHERE code = ?", (code,)
            ).fetchone()
        if row is None:
            return None
        return AuthorizationCode(
            code=row["code"],
            client_id=row["client_id"],
            scopes=_split(row["scopes"]),
            code_challenge=row["code_challenge"],
            redirect_uri=AnyUrl(row["redirect_uri"]),
            redirect_uri_provided_explicitly=bool(row["redirect_uri_provided_explicitly"]),
            resource=row["resource"],
            expires_at=row["expires_at"],
        )

    def delete_auth_code(self, code: str) -> None:
        with self._lock:
            self._db.execute("DELETE FROM auth_codes WHERE code = ?", (code,))
            self._db.commit()

    # -- access tokens --------------------------------------------------------

    def add_access_token(self, token: AccessToken) -> None:
        with self._lock:
            self._db.execute(
                "INSERT INTO access_tokens (token, client_id, scopes, resource, expires_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    token.token,
                    token.client_id,
                    _join(token.scopes),
                    token.resource,
                    token.expires_at,
                ),
            )
            self._db.commit()

    def get_access_token(self, token: str) -> AccessToken | None:
        with self._lock:
            row = self._db.execute(
                "SELECT * FROM access_tokens WHERE token = ?", (token,)
            ).fetchone()
        if row is None:
            return None
        return AccessToken(
            token=row["token"],
            client_id=row["client_id"],
            scopes=_split(row["scopes"]),
            resource=row["resource"],
            expires_at=row["expires_at"],
        )

    def delete_access_token(self, token: str) -> None:
        with self._lock:
            self._db.execute("DELETE FROM access_tokens WHERE token = ?", (token,))
            self._db.commit()

    # -- refresh tokens -------------------------------------------------------

    def add_refresh_token(self, token: RefreshToken, *, access_token: str) -> None:
        with self._lock:
            self._db.execute(
                "INSERT INTO refresh_tokens (token, client_id, scopes, access_token, expires_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (token.token, token.client_id, _join(token.scopes), access_token, token.expires_at),
            )
            self._db.commit()

    def get_refresh_token(self, token: str) -> RefreshToken | None:
        with self._lock:
            row = self._db.execute(
                "SELECT * FROM refresh_tokens WHERE token = ?", (token,)
            ).fetchone()
        if row is None:
            return None
        return RefreshToken(
            token=row["token"],
            client_id=row["client_id"],
            scopes=_split(row["scopes"]),
            expires_at=row["expires_at"],
        )

    def delete_refresh_token(self, token: str) -> str | None:
        """Delete a refresh token; return its paired access token (for cascade revoke)."""
        with self._lock:
            row = self._db.execute(
                "SELECT access_token FROM refresh_tokens WHERE token = ?", (token,)
            ).fetchone()
            self._db.execute("DELETE FROM refresh_tokens WHERE token = ?", (token,))
            self._db.commit()
        return row["access_token"] if row else None

    def delete_refresh_tokens_for_access_token(self, access_token: str) -> None:
        with self._lock:
            self._db.execute(
                "DELETE FROM refresh_tokens WHERE access_token = ?", (access_token,)
            )
            self._db.commit()
