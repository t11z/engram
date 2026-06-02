"""SQLite FTS5 search index — a rebuildable cache over the filesystem.

Rows are keyed by a stable surrogate ``noteid`` (also the FTS rowid), with the
vault-relative ``path`` as the canonical external handle and an optional ULID
``id`` alias. A note is addressed by path or by id; the surrogate keeps the link
graph and FTS rows stable across renames. Trashed notes keep their rows
(``deleted_at`` set) and are excluded from live search/list by the query filter.
"""

from __future__ import annotations

import base64
import json
import sqlite3
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

from .errors import IndexUnavailable
from .links import LinkResolver, extract_inline_tags, extract_links
from .models import (
    Note,
    NoteSummary,
    OutgoingLink,
    SearchResult,
    TagCount,
    from_rfc3339,
    to_rfc3339,
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS notes (
    noteid          INTEGER PRIMARY KEY,
    id              TEXT,
    path            TEXT NOT NULL,
    title           TEXT NOT NULL,
    tags_json       TEXT NOT NULL DEFAULT '[]',
    tags_text       TEXT NOT NULL DEFAULT '',
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    idempotency_key TEXT,
    size            INTEGER NOT NULL,
    mtime           REAL NOT NULL,
    deleted_at      TEXT,
    etag            TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_notes_id ON notes(id) WHERE id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_notes_path ON notes(path);
CREATE INDEX IF NOT EXISTS idx_notes_live ON notes(deleted_at, updated_at DESC, noteid DESC);
CREATE UNIQUE INDEX IF NOT EXISTS idx_notes_idem ON notes(idempotency_key)
    WHERE idempotency_key IS NOT NULL AND deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS links (
    src_noteid INTEGER NOT NULL,
    dst_raw    TEXT NOT NULL,
    link_type  TEXT NOT NULL,
    dst_noteid INTEGER
);
CREATE INDEX IF NOT EXISTS idx_links_src ON links(src_noteid);
CREATE INDEX IF NOT EXISTS idx_links_dst ON links(dst_noteid);

CREATE TABLE IF NOT EXISTS note_tags (
    noteid INTEGER NOT NULL,
    tag    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_note_tags_tag ON note_tags(tag);
CREATE INDEX IF NOT EXISTS idx_note_tags_noteid ON note_tags(noteid);
"""

_FTS = (
    "CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts "
    "USING fts5(title, body, tags, tokenize='unicode61 remove_diacritics 2')"
)

_BODY_COL = 1  # index of 'body' among the FTS columns (title, body, tags)


def _tags_text(tags: list[str]) -> str:
    return f" {' '.join(tags)} " if tags else ""


def _merge_tags(frontmatter: list[str], inline: list[str]) -> list[str]:
    """Union of frontmatter and inline tags, frontmatter first, de-duplicated."""
    merged = list(frontmatter)
    seen = set(frontmatter)
    for tag in inline:
        if tag not in seen:
            seen.add(tag)
            merged.append(tag)
    return merged


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
            # Upgrade an index created before the etag column existed.
            cols = {row[1] for row in conn.execute("PRAGMA table_info(notes)").fetchall()}
            if "etag" not in cols:
                conn.execute("ALTER TABLE notes ADD COLUMN etag TEXT")
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
        self,
        note: Note,
        *,
        size: int,
        mtime: float,
        etag: str | None = None,
        deleted_at: datetime | None = None,
    ) -> int:
        """Insert or update a note's row, matched by ``id`` (if any) else ``path``.
        ``etag`` is the content-hash version token (ADR-0009). Returns the
        surrogate ``noteid``.
        """
        deleted = to_rfc3339(deleted_at) if deleted_at is not None else None
        # Filtering and the FTS tags column cover the union of frontmatter and
        # inline #tags; the displayed tags (tags_json) stay frontmatter-only so
        # the on-disk model round-trips faithfully.
        all_tags = _merge_tags(note.tags, extract_inline_tags(note.body))
        fts_tags = " ".join(all_tags)
        with self.conn:
            noteid = self._match_noteid(note)
            values = (
                note.id,
                note.path,
                note.title,
                json.dumps(list(note.tags)),
                _tags_text(all_tags),
                to_rfc3339(note.created_at),
                to_rfc3339(note.updated_at),
                note.idempotency_key,
                size,
                mtime,
                deleted,
                etag,
            )
            if noteid is None:
                cur = self.conn.execute(
                    "INSERT INTO notes(id,path,title,tags_json,tags_text,created_at,updated_at,"
                    "idempotency_key,size,mtime,deleted_at,etag) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                    values,
                )
                noteid = int(cur.lastrowid or 0)
            else:
                self.conn.execute(
                    "UPDATE notes SET id=?,path=?,title=?,tags_json=?,tags_text=?,created_at=?,"
                    "updated_at=?,idempotency_key=?,size=?,mtime=?,deleted_at=?,etag=? "
                    "WHERE noteid=?",
                    (*values, noteid),
                )
                self.conn.execute("DELETE FROM notes_fts WHERE rowid = ?", (noteid,))
            self.conn.execute(
                "INSERT INTO notes_fts(rowid, title, body, tags) VALUES(?,?,?,?)",
                (noteid, note.title, note.body, fts_tags),
            )
            self.conn.execute("DELETE FROM links WHERE src_noteid = ?", (noteid,))
            if deleted_at is None:
                rows = [
                    (noteid, link.target, link.type, None) for link in extract_links(note.body)
                ]
                if rows:
                    self.conn.executemany(
                        "INSERT INTO links(src_noteid, dst_raw, link_type, dst_noteid) "
                        "VALUES(?,?,?,?)",
                        rows,
                    )
            self.conn.execute("DELETE FROM note_tags WHERE noteid = ?", (noteid,))
            if deleted_at is None and all_tags:
                self.conn.executemany(
                    "INSERT INTO note_tags(noteid, tag) VALUES(?,?)",
                    [(noteid, tag) for tag in all_tags],
                )
            return noteid

    def move_row(
        self, old_path: str, new_path: str, *, size: int, mtime: float, deleted_at: datetime | None
    ) -> None:
        """Update the path/state of the row at ``old_path`` (used by delete/restore,
        where the file moves but the note's identity is unchanged).
        """
        deleted = to_rfc3339(deleted_at) if deleted_at is not None else None
        with self.conn:
            self.conn.execute(
                "UPDATE notes SET path=?, size=?, mtime=?, deleted_at=? WHERE path=?",
                (new_path, size, mtime, deleted, old_path),
            )

    def remove_noteid(self, noteid: int) -> None:
        with self.conn:
            self.conn.execute("DELETE FROM notes_fts WHERE rowid = ?", (noteid,))
            self.conn.execute("DELETE FROM notes WHERE noteid = ?", (noteid,))
            self.conn.execute("DELETE FROM links WHERE src_noteid = ?", (noteid,))
            self.conn.execute("UPDATE links SET dst_noteid = NULL WHERE dst_noteid = ?", (noteid,))
            self.conn.execute("DELETE FROM note_tags WHERE noteid = ?", (noteid,))

    def remove_path(self, path: str) -> None:
        row = self.conn.execute("SELECT noteid FROM notes WHERE path = ?", (path,)).fetchone()
        if row is not None:
            self.remove_noteid(int(row[0]))

    def clear(self) -> None:
        with self.conn:
            self.conn.execute("DELETE FROM notes_fts")
            self.conn.execute("DELETE FROM notes")
            self.conn.execute("DELETE FROM links")
            self.conn.execute("DELETE FROM note_tags")

    def resolve_links(self) -> None:
        """Recompute ``dst_noteid`` for every link against the current live notes."""
        with self.conn:
            live = self.conn.execute(
                "SELECT noteid, path FROM notes WHERE deleted_at IS NULL"
            ).fetchall()
            resolver = LinkResolver([str(r[1]) for r in live])
            path_to_noteid = {str(r[1]): int(r[0]) for r in live}
            src_paths = {
                int(r[0]): str(r[1])
                for r in self.conn.execute("SELECT noteid, path FROM notes").fetchall()
            }
            updates: list[tuple[int | None, int]] = []
            for rowid, src_noteid, dst_raw, link_type in self.conn.execute(
                "SELECT rowid, src_noteid, dst_raw, link_type FROM links"
            ).fetchall():
                src_path = src_paths.get(int(src_noteid), "")
                dst_path = resolver.resolve(str(link_type), str(dst_raw), src_path)
                dst_noteid = path_to_noteid.get(dst_path) if dst_path is not None else None
                updates.append((dst_noteid, int(rowid)))
            if updates:
                self.conn.executemany(
                    "UPDATE links SET dst_noteid = ? WHERE rowid = ?", updates
                )

    # --- reads --------------------------------------------------------------

    def resolve_handle(self, handle: str) -> str | None:
        """Live path for a handle that is either a note id or a vault-relative path."""
        row = self.conn.execute(
            "SELECT path FROM notes WHERE id = ? AND deleted_at IS NULL", (handle,)
        ).fetchone()
        if row is not None:
            return str(row[0])
        row = self.conn.execute(
            "SELECT path FROM notes WHERE path = ? AND deleted_at IS NULL", (handle,)
        ).fetchone()
        return None if row is None else str(row[0])

    def etag_for(self, handle: str) -> str | None:
        """Cached content-hash token for a live note addressed by id or path."""
        for column in ("id", "path"):
            row = self.conn.execute(
                f"SELECT etag FROM notes WHERE {column} = ? AND deleted_at IS NULL", (handle,)
            ).fetchone()
            if row is not None:
                return None if row[0] is None else str(row[0])
        return None

    def find_by_idempotency_key(self, key: str) -> str | None:
        row = self.conn.execute(
            "SELECT path FROM notes WHERE idempotency_key = ? AND deleted_at IS NULL", (key,)
        ).fetchone()
        return None if row is None else str(row[0])

    def backlinks(self, handle: str) -> list[NoteSummary]:
        """Live notes that link to the note identified by ``handle`` (newest first)."""
        noteid = self._resolve_noteid(handle, live_only=True)
        if noteid is None:
            return []
        sql = (
            "SELECT DISTINCT n.id, n.title, n.tags_json, n.updated_at, n.path "
            "FROM links l JOIN notes n ON n.noteid = l.src_noteid "
            "WHERE l.dst_noteid = ? AND n.deleted_at IS NULL "
            "ORDER BY n.updated_at DESC, n.noteid DESC"
        )
        return [_summary(r) for r in self.conn.execute(sql, (noteid,)).fetchall()]

    def outgoing_links(self, handle: str) -> list[OutgoingLink]:
        """Outgoing references from ``handle``; ``resolved_*`` is None if dangling."""
        noteid = self._resolve_noteid(handle, live_only=True)
        if noteid is None:
            return []
        sql = (
            "SELECT l.dst_raw, l.link_type, n.id, n.path "
            "FROM links l LEFT JOIN notes n ON n.noteid = l.dst_noteid AND n.deleted_at IS NULL "
            "WHERE l.src_noteid = ?"
        )
        return [
            OutgoingLink(
                target=str(r[0]),
                type=str(r[1]),
                resolved_id=str(r[2]) if r[2] is not None else None,
                resolved_path=str(r[3]) if r[3] is not None else None,
            )
            for r in self.conn.execute(sql, (noteid,)).fetchall()
        ]

    def get_summary(self, path: str) -> NoteSummary | None:
        """Summary for a live note by path (for graph/related projections)."""
        row = self.conn.execute(
            "SELECT id, title, tags_json, updated_at, path FROM notes "
            "WHERE path = ? AND deleted_at IS NULL",
            (path,),
        ).fetchone()
        return None if row is None else _summary(row)

    def find_by_title(self, title: str) -> str | None:
        """Path of the most recently updated live note with this exact title."""
        row = self.conn.execute(
            "SELECT path FROM notes WHERE title = ? AND deleted_at IS NULL "
            "ORDER BY updated_at DESC, noteid DESC LIMIT 1",
            (title,),
        ).fetchone()
        return None if row is None else str(row[0])

    def backlink_edges(self, handle: str) -> list[tuple[str, str]]:
        """(source path, link type) for live notes linking to ``handle``."""
        noteid = self._resolve_noteid(handle, live_only=True)
        if noteid is None:
            return []
        sql = (
            "SELECT n.path, l.link_type FROM links l JOIN notes n ON n.noteid = l.src_noteid "
            "WHERE l.dst_noteid = ? AND n.deleted_at IS NULL"
        )
        return [(str(r[0]), str(r[1])) for r in self.conn.execute(sql, (noteid,)).fetchall()]

    def list_folders(self) -> list[str]:
        """Distinct folders (and their ancestors) containing live notes, sorted."""
        folders: set[str] = set()
        for row in self.conn.execute(
            "SELECT path FROM notes WHERE deleted_at IS NULL"
        ).fetchall():
            parts = str(row[0]).split("/")[:-1]
            for i in range(1, len(parts) + 1):
                folders.add("/".join(parts[:i]))
        return sorted(folders)

    def list_tags(self) -> list[TagCount]:
        """All tags on live notes (frontmatter and inline) with counts, by frequency."""
        rows = self.conn.execute(
            "SELECT nt.tag, COUNT(*) FROM note_tags nt JOIN notes n ON n.noteid = nt.noteid "
            "WHERE n.deleted_at IS NULL GROUP BY nt.tag ORDER BY COUNT(*) DESC, nt.tag"
        ).fetchall()
        return [TagCount(tag=str(r[0]), count=int(r[1])) for r in rows]

    def all_rows(self) -> Iterator[tuple[int, str | None, str, int, float, str | None]]:
        for row in self.conn.execute(
            "SELECT noteid, id, path, size, mtime, deleted_at FROM notes"
        ).fetchall():
            yield (int(row[0]), row[1], str(row[2]), int(row[3]), float(row[4]), row[5])

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
            "FROM notes_fts JOIN notes n ON n.noteid = notes_fts.rowid "
            f"WHERE {' AND '.join(conds)} ORDER BY rank LIMIT ?"
        )
        results: list[SearchResult] = []
        for row in self.conn.execute(sql, params).fetchall():
            results.append(
                SearchResult(
                    id=row[0],
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

    def _match_noteid(self, note: Note) -> int | None:
        if note.id is not None:
            row = self.conn.execute("SELECT noteid FROM notes WHERE id = ?", (note.id,)).fetchone()
            if row is not None:
                return int(row[0])
        row = self.conn.execute("SELECT noteid FROM notes WHERE path = ?", (note.path,)).fetchone()
        return None if row is None else int(row[0])

    def _resolve_noteid(self, handle: str, *, live_only: bool) -> int | None:
        suffix = " AND deleted_at IS NULL" if live_only else ""
        row = self.conn.execute(
            f"SELECT noteid FROM notes WHERE id = ?{suffix}", (handle,)
        ).fetchone()
        if row is not None:
            return int(row[0])
        row = self.conn.execute(
            f"SELECT noteid FROM notes WHERE path = ?{suffix}", (handle,)
        ).fetchone()
        return None if row is None else int(row[0])

    def _paginate(
        self, *, trashed: bool, tag: str | None, limit: int, cursor: str | None
    ) -> tuple[list[NoteSummary], str | None]:
        sort_col = "deleted_at" if trashed else "updated_at"
        key_idx = 5 if trashed else 3  # deleted_at vs updated_at in the SELECT below
        conds = ["deleted_at IS NOT NULL" if trashed else "deleted_at IS NULL"]
        params: list[object] = []
        if tag:
            conds.append("tags_text LIKE ?")
            params.append(f"% {tag} %")
        if cursor is not None:
            key, cid = _decode_cursor(cursor)
            conds.append(f"({sort_col}, noteid) < (?, ?)")
            params.extend([key, int(cid)])
        params.append(limit + 1)
        sql = (
            "SELECT id, title, tags_json, updated_at, path, deleted_at, noteid FROM notes "
            f"WHERE {' AND '.join(conds)} ORDER BY {sort_col} DESC, noteid DESC LIMIT ?"
        )
        rows = self.conn.execute(sql, params).fetchall()
        has_more = len(rows) > limit
        rows = rows[:limit]
        summaries = [_summary(r) for r in rows]
        next_cursor = (
            _encode_cursor(str(rows[-1][key_idx]), str(rows[-1][6])) if has_more else None
        )
        return summaries, next_cursor


def _summary(row: tuple[object, ...]) -> NoteSummary:
    return NoteSummary(
        id=row[0] if row[0] is None else str(row[0]),
        title=str(row[1]),
        tags=list(json.loads(str(row[2]))),
        updated_at=from_rfc3339(str(row[3])),
        path=str(row[4]),
    )


def _encode_cursor(key: str, noteid: str) -> str:
    return base64.urlsafe_b64encode(f"{key}|{noteid}".encode()).decode("ascii")


def _decode_cursor(cursor: str) -> tuple[str, str]:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
        key, noteid = raw.split("|", 1)
    except (ValueError, UnicodeDecodeError) as exc:
        raise ValueError("invalid pagination cursor") from exc
    return key, noteid
