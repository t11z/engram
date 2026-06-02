"""SQLite FTS5 search index — a rebuildable cache over the filesystem.

Holds a ``notes`` metadata table (for typed sort/filter/pagination, idempotency
lookup, and path resolution) plus a standalone ``notes_fts`` FTS5 table keyed by a
shared rowid. Trashed notes keep their rows (``deleted_at`` set) and are excluded
from live search/list by the query filter. The body text lives only in the FTS
table; full note content is always read from disk via the path.
"""

from __future__ import annotations

import base64
import json
import sqlite3
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

from .errors import IndexUnavailable
from .links import LinkResolver, extract_links
from .models import Note, NoteSummary, OutgoingLink, SearchResult, from_rfc3339, to_rfc3339

_SCHEMA = """
CREATE TABLE IF NOT EXISTS notes (
    id              TEXT PRIMARY KEY,
    path            TEXT NOT NULL,
    title           TEXT NOT NULL,
    tags_json       TEXT NOT NULL DEFAULT '[]',
    tags_text       TEXT NOT NULL DEFAULT '',
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    idempotency_key TEXT,
    size            INTEGER NOT NULL,
    mtime           REAL NOT NULL,
    deleted_at      TEXT
);
CREATE INDEX IF NOT EXISTS idx_notes_live ON notes(deleted_at, updated_at DESC, id DESC);
CREATE UNIQUE INDEX IF NOT EXISTS idx_notes_idem ON notes(idempotency_key)
    WHERE idempotency_key IS NOT NULL AND deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS links (
    src_id    TEXT NOT NULL,
    dst_raw   TEXT NOT NULL,
    link_type TEXT NOT NULL,
    dst_id    TEXT
);
CREATE INDEX IF NOT EXISTS idx_links_src ON links(src_id);
CREATE INDEX IF NOT EXISTS idx_links_dst ON links(dst_id);
"""

_FTS = (
    "CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts "
    "USING fts5(title, body, tags, tokenize='unicode61 remove_diacritics 2')"
)

_BODY_COL = 1  # index of 'body' among the FTS columns (title, body, tags)


def _tags_text(tags: list[str]) -> str:
    return f" {' '.join(tags)} " if tags else ""


def _build_match(query: str) -> str | None:
    """Turn a user query into a safe FTS5 MATCH string (quoted AND-ed terms)."""
    tokens = query.split()
    if not tokens:
        return None
    return " ".join('"' + token.replace('"', '""') + '"' for token in tokens)


class SearchIndex:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._conn: sqlite3.Connection | None = None

    # --- lifecycle ----------------------------------------------------------

    def open(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA busy_timeout=5000")
        try:
            conn.executescript(_SCHEMA)
            conn.execute(_FTS)
        except sqlite3.OperationalError as exc:
            conn.close()
            if "fts5" in str(exc).lower():
                raise IndexUnavailable(
                    "This SQLite build lacks FTS5 support, which Engram requires."
                ) from exc
            raise
        conn.commit()
        self._conn = conn

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError("SearchIndex is not open; call open() first.")
        return self._conn

    # --- writes -------------------------------------------------------------

    def upsert(
        self, note: Note, *, size: int, mtime: float, deleted_at: datetime | None = None
    ) -> None:
        deleted = to_rfc3339(deleted_at) if deleted_at is not None else None
        fts_tags = " ".join(note.tags)
        with self.conn:
            row = self.conn.execute("SELECT rowid FROM notes WHERE id = ?", (note.id,)).fetchone()
            values = (
                note.path,
                note.title,
                json.dumps(list(note.tags)),
                _tags_text(note.tags),
                to_rfc3339(note.created_at),
                to_rfc3339(note.updated_at),
                note.idempotency_key,
                size,
                mtime,
                deleted,
            )
            if row is None:
                cur = self.conn.execute(
                    "INSERT INTO notes(path,title,tags_json,tags_text,created_at,updated_at,"
                    "idempotency_key,size,mtime,deleted_at,id) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                    (*values, note.id),
                )
                rowid = cur.lastrowid
            else:
                rowid = row[0]
                self.conn.execute(
                    "UPDATE notes SET path=?,title=?,tags_json=?,tags_text=?,created_at=?,"
                    "updated_at=?,idempotency_key=?,size=?,mtime=?,deleted_at=? WHERE id=?",
                    (*values, note.id),
                )
                self.conn.execute("DELETE FROM notes_fts WHERE rowid = ?", (rowid,))
            self.conn.execute(
                "INSERT INTO notes_fts(rowid, title, body, tags) VALUES(?,?,?,?)",
                (rowid, note.title, note.body, fts_tags),
            )
            self.conn.execute("DELETE FROM links WHERE src_id = ?", (note.id,))
            if deleted_at is None:
                link_rows = [
                    (note.id, link.target, link.type, None)
                    for link in extract_links(note.body)
                ]
                if link_rows:
                    self.conn.executemany(
                        "INSERT INTO links(src_id, dst_raw, link_type, dst_id) "
                        "VALUES(?,?,?,?)",
                        link_rows,
                    )

    def mark_trashed(self, note_id: str, path: str, deleted_at: datetime) -> None:
        with self.conn:
            self.conn.execute(
                "UPDATE notes SET deleted_at = ?, path = ? WHERE id = ?",
                (to_rfc3339(deleted_at), path, note_id),
            )

    def unmark_trashed(self, note_id: str, path: str) -> None:
        with self.conn:
            self.conn.execute(
                "UPDATE notes SET deleted_at = NULL, path = ? WHERE id = ?",
                (path, note_id),
            )

    def remove(self, note_id: str) -> None:
        with self.conn:
            row = self.conn.execute("SELECT rowid FROM notes WHERE id = ?", (note_id,)).fetchone()
            if row is None:
                return
            self.conn.execute("DELETE FROM notes_fts WHERE rowid = ?", (row[0],))
            self.conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
            self.conn.execute("DELETE FROM links WHERE src_id = ?", (note_id,))
            self.conn.execute("UPDATE links SET dst_id = NULL WHERE dst_id = ?", (note_id,))

    def clear(self) -> None:
        with self.conn:
            self.conn.execute("DELETE FROM notes_fts")
            self.conn.execute("DELETE FROM notes")
            self.conn.execute("DELETE FROM links")

    def resolve_links(self) -> None:
        """Recompute ``dst_id`` for every link row against the current live notes.

        Cheap to run after any single write and once at the end of a bulk
        reconcile/reindex; keeps dangling links and rename effects globally
        consistent without incremental bookkeeping.
        """
        with self.conn:
            live = self.conn.execute(
                "SELECT id, path FROM notes WHERE deleted_at IS NULL"
            ).fetchall()
            resolver = LinkResolver([str(r[1]) for r in live])
            path_to_id = {str(r[1]): str(r[0]) for r in live}
            src_paths = {
                str(r[0]): str(r[1])
                for r in self.conn.execute("SELECT id, path FROM notes").fetchall()
            }
            updates: list[tuple[str | None, int]] = []
            for rowid, src_id, dst_raw, link_type in self.conn.execute(
                "SELECT rowid, src_id, dst_raw, link_type FROM links"
            ).fetchall():
                src_path = src_paths.get(str(src_id), "")
                dst_path = resolver.resolve(str(link_type), str(dst_raw), src_path)
                dst_id = path_to_id.get(dst_path) if dst_path is not None else None
                updates.append((dst_id, int(rowid)))
            if updates:
                self.conn.executemany("UPDATE links SET dst_id = ? WHERE rowid = ?", updates)

    # --- reads --------------------------------------------------------------

    def get_path(self, note_id: str) -> str | None:
        row = self.conn.execute(
            "SELECT path FROM notes WHERE id = ? AND deleted_at IS NULL", (note_id,)
        ).fetchone()
        return None if row is None else str(row[0])

    def find_by_idempotency_key(self, key: str) -> str | None:
        row = self.conn.execute(
            "SELECT id FROM notes WHERE idempotency_key = ? AND deleted_at IS NULL", (key,)
        ).fetchone()
        return None if row is None else str(row[0])

    def backlinks(self, note_id: str) -> list[NoteSummary]:
        """Live notes that link to ``note_id`` (newest first)."""
        sql = (
            "SELECT DISTINCT n.id, n.title, n.tags_json, n.updated_at, n.path "
            "FROM links l JOIN notes n ON n.id = l.src_id "
            "WHERE l.dst_id = ? AND n.deleted_at IS NULL "
            "ORDER BY n.updated_at DESC, n.id DESC"
        )
        return [
            NoteSummary(
                id=str(r[0]),
                title=str(r[1]),
                tags=list(json.loads(r[2])),
                updated_at=from_rfc3339(str(r[3])),
                path=str(r[4]),
            )
            for r in self.conn.execute(sql, (note_id,)).fetchall()
        ]

    def outgoing_links(self, note_id: str) -> list[OutgoingLink]:
        """Outgoing references from ``note_id``; ``resolved_*`` is None if dangling."""
        sql = (
            "SELECT l.dst_raw, l.link_type, l.dst_id, n.path "
            "FROM links l LEFT JOIN notes n ON n.id = l.dst_id AND n.deleted_at IS NULL "
            "WHERE l.src_id = ?"
        )
        return [
            OutgoingLink(
                target=str(r[0]),
                type=str(r[1]),
                resolved_id=str(r[2]) if r[2] is not None else None,
                resolved_path=str(r[3]) if r[3] is not None else None,
            )
            for r in self.conn.execute(sql, (note_id,)).fetchall()
        ]

    def all_rows(self) -> Iterator[tuple[str, str, int, float, str | None]]:
        for row in self.conn.execute(
            "SELECT id, path, size, mtime, deleted_at FROM notes"
        ).fetchall():
            yield (str(row[0]), str(row[1]), int(row[2]), float(row[3]), row[4])

    def search(self, query: str, *, tag: str | None = None, limit: int = 20) -> list[SearchResult]:
        match = _build_match(query)
        if match is None:
            return []
        conds = ["notes_fts MATCH ?", "n.deleted_at IS NULL"]
        params: list[object] = [match]
        if tag:
            conds.append("n.tags_text LIKE ?")
            params.append(f"% {tag} %")
        params.append(limit)
        sql = (
            "SELECT n.id, n.title, n.tags_json, n.updated_at, n.path, "
            f"bm25(notes_fts) AS rank, snippet(notes_fts, {_BODY_COL}, '', '', '…', 12) AS snip "
            "FROM notes_fts JOIN notes n ON n.rowid = notes_fts.rowid "
            f"WHERE {' AND '.join(conds)} ORDER BY rank LIMIT ?"
        )
        results: list[SearchResult] = []
        for row in self.conn.execute(sql, params).fetchall():
            results.append(
                SearchResult(
                    id=str(row[0]),
                    title=str(row[1]),
                    tags=list(json.loads(row[2])),
                    updated_at=from_rfc3339(str(row[3])),
                    path=str(row[4]),
                    score=-float(row[5]),
                    snippet=str(row[6]),
                )
            )
        return results

    def list_live(
        self, *, tag: str | None = None, limit: int = 50, cursor: str | None = None
    ) -> tuple[list[NoteSummary], str | None]:
        return self._paginate(trashed=False, tag=tag, limit=limit, cursor=cursor)

    def list_trash(
        self, *, limit: int = 50, cursor: str | None = None
    ) -> tuple[list[NoteSummary], str | None]:
        return self._paginate(trashed=True, tag=None, limit=limit, cursor=cursor)

    # --- internals ----------------------------------------------------------

    def _paginate(
        self, *, trashed: bool, tag: str | None, limit: int, cursor: str | None
    ) -> tuple[list[NoteSummary], str | None]:
        sort_col = "deleted_at" if trashed else "updated_at"
        key_idx = 4 if trashed else 3  # deleted_at vs updated_at in the SELECT below
        conds = ["deleted_at IS NOT NULL" if trashed else "deleted_at IS NULL"]
        params: list[object] = []
        if tag:
            conds.append("tags_text LIKE ?")
            params.append(f"% {tag} %")
        if cursor is not None:
            key, cid = _decode_cursor(cursor)
            conds.append(f"({sort_col}, id) < (?, ?)")
            params.extend([key, cid])
        params.append(limit + 1)
        sql = (
            "SELECT id, title, tags_json, updated_at, deleted_at, path FROM notes "
            f"WHERE {' AND '.join(conds)} ORDER BY {sort_col} DESC, id DESC LIMIT ?"
        )
        rows = self.conn.execute(sql, params).fetchall()
        has_more = len(rows) > limit
        rows = rows[:limit]
        summaries = [
            NoteSummary(
                id=str(r[0]),
                title=str(r[1]),
                tags=list(json.loads(r[2])),
                updated_at=from_rfc3339(str(r[3])),
                path=str(r[5]),
            )
            for r in rows
        ]
        next_cursor = _encode_cursor(str(rows[-1][key_idx]), str(rows[-1][0])) if has_more else None
        return summaries, next_cursor


def _encode_cursor(key: str, note_id: str) -> str:
    return base64.urlsafe_b64encode(f"{key}|{note_id}".encode()).decode("ascii")


def _decode_cursor(cursor: str) -> tuple[str, str]:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
        key, note_id = raw.split("|", 1)
    except (ValueError, UnicodeDecodeError) as exc:
        raise ValueError("invalid pagination cursor") from exc
    return key, note_id
