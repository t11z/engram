"""``NoteService``: the public API that REST and MCP build on.

Composes the filesystem ``VaultStore`` (source of truth) and the ``SearchIndex``
(rebuildable cache), enforcing write-through ordering (file write is the commit
point, index follows) and idempotency. No web framework is imported here.
"""

from __future__ import annotations

import mimetypes
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256

from .config import Settings
from .config_detect import detect_vault_config
from .editing import append_body, replace_section
from .errors import NoteConflict, NoteNotFound
from .frontmatter import read_note_file
from .ids import new_ulid
from .index import SearchIndex
from .link_extractor import LinkFetchSettings, fetch_and_extract
from .models import (
    AttachmentInfo,
    GraphEdge,
    GraphNode,
    GraphView,
    Note,
    NoteCreate,
    NoteSummary,
    OutgoingLink,
    SearchResult,
    TagCount,
)
from .store import VaultStore


@dataclass
class ReconcileReport:
    indexed: int
    removed: int


@dataclass
class ReindexReport:
    live: int
    trash: int


class NoteService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        # Fill unset dirs from a well-known editor config in the vault, if present.
        detected = detect_vault_config(settings.vault_path)
        self.new_note_dir = settings.new_note_dir or detected.get("new_note_dir", "")
        self.attachment_dir = settings.attachment_dir or detected.get("attachment_dir", "")
        self.daily_note_dir = settings.daily_note_dir or detected.get("daily_note_dir", "")
        self.store = VaultStore(settings.vault_path, self.new_note_dir)
        self.index = SearchIndex(settings.resolved_index_path)

    @classmethod
    def from_env(cls) -> NoteService:
        return cls(Settings())

    def startup(self) -> None:
        self.store.ensure_layout()
        self.index.open()
        self.reconcile()

    def close(self) -> None:
        self.index.close()

    # --- commands -----------------------------------------------------------

    def create(self, data: NoteCreate, *, now: datetime | None = None) -> tuple[Note, bool]:
        """Create a note. Returns ``(note, created)``; ``created`` is False when an
        existing live note is returned for a repeated ``idempotency_key``.
        """
        if data.idempotency_key:
            existing = self.index.find_by_idempotency_key(data.idempotency_key)
            if existing is not None:
                return self.get(existing), False
        ts = now or datetime.now(UTC)
        note = Note(
            id=new_ulid() if self.settings.inject_id else None,
            title=data.title,
            created_at=ts,
            updated_at=ts,
            tags=list(data.tags),
            source_url=data.source_url,
            idempotency_key=data.idempotency_key,
            body=data.body,
            path="",
        )
        stored = self.store.write(note)
        abs_path = self.settings.vault_path / stored.path
        size, mtime = self.store.stat(abs_path)
        etag = self.store.content_hash(abs_path)
        self.index.upsert(stored, size=size, mtime=mtime, etag=etag)
        self.index.resolve_links()
        return stored, True

    def delete(self, handle: str, *, now: datetime | None = None) -> None:
        """Soft-delete: move to trash and mark the index row trashed.

        ``handle`` is a note's path or its id alias.
        """
        ts = now or datetime.now(UTC)
        note = self.get(handle)  # raises NoteNotFound if not live
        trash_path = self.store.move_to_trash(note.path, ts)
        size, mtime = self.store.stat(self.settings.vault_path / trash_path)
        self.index.move_row(note.path, trash_path, size=size, mtime=mtime, deleted_at=ts)
        self.index.resolve_links()

    def restore(self, trash_path: str) -> Note:
        """Restore a trashed note by its trash-relative path (``.trash/<subpath>``)."""
        note = self.store.restore(trash_path)  # raises NoteNotInTrash
        size, mtime = self.store.stat(self.settings.vault_path / note.path)
        self.index.move_row(trash_path, note.path, size=size, mtime=mtime, deleted_at=None)
        self.index.resolve_links()
        return note

    # --- in-place editing (ADR-0009) ----------------------------------------

    def _edit(
        self,
        handle: str,
        mutate: Callable[[Note], Note],
        *,
        expected_etag: str | None,
        now: datetime | None,
    ) -> Note:
        """Read a live note, optionally enforce an `If-Match` precondition, apply
        ``mutate`` to it, write it back in place, and re-index. Raises
        ``NoteConflict`` if the note changed since ``expected_etag`` was read.
        """
        note = self.get(handle)
        if expected_etag is not None and self.index.etag_for(note.path) != expected_etag:
            raise NoteConflict(handle)
        ts = now or datetime.now(UTC)
        edited = mutate(note).model_copy(update={"updated_at": ts})
        stored = self.store.write(edited)
        abs_path = self.settings.vault_path / stored.path
        size, mtime = self.store.stat(abs_path)
        self.index.upsert(stored, size=size, mtime=mtime, etag=self.store.content_hash(abs_path))
        self.index.resolve_links()
        return stored

    def update_note(
        self,
        handle: str,
        *,
        title: str | None = None,
        body: str | None = None,
        tags: list[str] | None = None,
        expected_etag: str | None = None,
        now: datetime | None = None,
    ) -> Note:
        """Replace a note's title/body/tags (whichever are given). Precondition-
        guarded when ``expected_etag`` is supplied.
        """

        def mutate(note: Note) -> Note:
            updates: dict[str, object] = {}
            if title is not None:
                updates["title"] = title
            if body is not None:
                updates["body"] = body
            if tags is not None:
                updates["tags"] = list(tags)
            return note.model_copy(update=updates)

        return self._edit(handle, mutate, expected_etag=expected_etag, now=now)

    def append_to_note(self, handle: str, text: str, *, now: datetime | None = None) -> Note:
        """Append a Markdown block to a note's body (retry-safe; no precondition)."""
        return self._edit(
            handle,
            lambda note: note.model_copy(update={"body": append_body(note.body, text)}),
            expected_etag=None,
            now=now,
        )

    def patch_section(
        self, handle: str, heading: str, content: str, *, now: datetime | None = None
    ) -> Note:
        """Replace the section under ``heading`` (created if absent); retry-safe."""
        return self._edit(
            handle,
            lambda note: note.model_copy(
                update={"body": replace_section(note.body, heading, content)}
            ),
            expected_etag=None,
            now=now,
        )

    def purge_expired_trash(self, *, now: datetime | None = None) -> list[str]:
        ts = now or datetime.now(UTC)
        purged = self.store.purge_expired(self.settings.trash_retention_days, ts)
        for trash_path in purged:
            self.index.remove_path(trash_path)
        return purged

    # --- queries ------------------------------------------------------------

    def get(self, handle: str) -> Note:
        """Read a live note by its path or id alias. Raises ``NoteNotFound``."""
        path = self.index.resolve_handle(handle)
        if path is not None:
            abs_path = self.settings.vault_path / path
            if abs_path.exists():
                return read_note_file(abs_path, path)
        candidate = self.settings.vault_path / handle
        if handle.endswith(".md") and candidate.exists():
            return read_note_file(candidate, handle)
        by_id = self.store.path_for_id(handle)
        if by_id is not None:
            return self.store.read(by_id)
        raise NoteNotFound(handle)

    def list_notes(
        self, *, tag: str | None = None, limit: int = 50, cursor: str | None = None
    ) -> tuple[list[NoteSummary], str | None]:
        return self.index.list_live(tag=tag, limit=limit, cursor=cursor)

    def search(self, query: str, *, tag: str | None = None, limit: int = 20) -> list[SearchResult]:
        return self.index.search(query, tag=tag, limit=limit)

    def list_trash(
        self, *, limit: int = 50, cursor: str | None = None
    ) -> tuple[list[NoteSummary], str | None]:
        return self.index.list_trash(limit=limit, cursor=cursor)

    def get_etag(self, handle: str) -> str | None:
        """Content-hash version token for a live note (path or id). Used as the
        `If-Match` precondition for in-place edits. Raises ``NoteNotFound``.
        """
        note = self.get(handle)
        return self.index.etag_for(note.path)

    def get_backlinks(self, handle: str) -> list[NoteSummary]:
        """Live notes that link to ``handle`` (path or id). Raises ``NoteNotFound``."""
        note = self.get(handle)
        return self.index.backlinks(note.path)

    def get_outgoing_links(self, handle: str) -> list[OutgoingLink]:
        """Outgoing references from ``handle`` (path or id), resolved or dangling."""
        note = self.get(handle)
        return self.index.outgoing_links(note.path)

    def get_related(self, handle: str) -> list[NoteSummary]:
        """Notes one hop away: backlinks plus resolved outgoing targets, deduped."""
        note = self.get(handle)
        seen: set[str] = {note.path}
        related: list[NoteSummary] = []
        for summary in self.index.backlinks(note.path):
            if summary.path not in seen:
                seen.add(summary.path)
                related.append(summary)
        for link in self.index.outgoing_links(note.path):
            target = link.resolved_path
            if target is not None and target not in seen:
                target_summary = self.index.get_summary(target)
                if target_summary is not None:
                    seen.add(target)
                    related.append(target_summary)
        return related

    def get_graph(self, handle: str, *, depth: int = 1) -> GraphView:
        """A scoped link neighbourhood around a note, BFS-expanded to ``depth``."""
        note = self.get(handle)
        focus = note.path
        nodes: dict[str, GraphNode] = {}
        edges: list[GraphEdge] = []
        edge_seen: set[tuple[str, str, str]] = set()

        def add_node(path: str) -> bool:
            if path in nodes:
                return False
            summary = self.index.get_summary(path)
            title = summary.title if summary is not None else path
            node_id = summary.id if summary is not None else None
            nodes[path] = GraphNode(path=path, title=title, id=node_id)
            return True

        def add_edge(source: str, target: str, link_type: str) -> None:
            key = (source, target, link_type)
            if key not in edge_seen:
                edge_seen.add(key)
                edges.append(GraphEdge(source=source, target=target, type=link_type))

        add_node(focus)
        frontier = [focus]
        for _ in range(max(0, depth)):
            nxt: list[str] = []
            for path in frontier:
                for link in self.index.outgoing_links(path):
                    if link.resolved_path is not None:
                        is_new = add_node(link.resolved_path)
                        add_edge(path, link.resolved_path, link.type)
                        if is_new:
                            nxt.append(link.resolved_path)
                for source, link_type in self.index.backlink_edges(path):
                    is_new = add_node(source)
                    add_edge(source, path, link_type)
                    if is_new:
                        nxt.append(source)
            frontier = nxt
        return GraphView(focus=focus, nodes=list(nodes.values()), edges=edges)

    def get_by_title(self, title: str) -> Note:
        """Read the most recently updated live note with this exact title."""
        path = self.index.find_by_title(title)
        if path is None:
            raise NoteNotFound(title)
        return self.get(path)

    def list_folders(self) -> list[str]:
        """Folders (and ancestors) containing live notes."""
        return self.index.list_folders()

    def list_tags(self) -> list[TagCount]:
        """All tags on live notes (frontmatter and inline) with counts."""
        return self.index.list_tags()

    def list_attachments(self) -> list[AttachmentInfo]:
        """Non-Markdown files in the vault (optionally scoped to the attachment dir)."""
        prefix = f"{self.attachment_dir}/" if self.attachment_dir else ""
        out: list[AttachmentInfo] = []
        for rel, size in self.store.iter_attachments():
            if prefix and not rel.startswith(prefix):
                continue
            content_type = mimetypes.guess_type(rel)[0] or "application/octet-stream"
            out.append(AttachmentInfo(path=rel, size=size, content_type=content_type))
        return out

    def read_attachment(self, path: str) -> tuple[bytes, str]:
        """Bytes and content type of an attachment. Raises ``NoteNotFound`` if absent."""
        data = self.store.read_attachment(path)
        content_type = mimetypes.guess_type(path)[0] or "application/octet-stream"
        return data, content_type

    def append_to_daily_note(self, text: str, *, now: datetime | None = None) -> Note:
        """Append a block to today's daily note (``<daily_note_dir>/YYYY-MM-DD.md``),
        creating it if it doesn't exist yet.
        """
        ts = now or datetime.now(UTC)
        date = ts.strftime("%Y-%m-%d")
        rel = f"{self.daily_note_dir}/{date}.md" if self.daily_note_dir else f"{date}.md"
        if (self.settings.vault_path / rel).exists():
            return self.append_to_note(rel, text, now=ts)
        note = Note(
            id=new_ulid() if self.settings.inject_id else None,
            title=date,
            created_at=ts,
            updated_at=ts,
            tags=[],
            body=text,
            path=rel,
        )
        stored = self.store.write(note)
        abs_path = self.settings.vault_path / stored.path
        size, mtime = self.store.stat(abs_path)
        self.index.upsert(stored, size=size, mtime=mtime, etag=self.store.content_hash(abs_path))
        self.index.resolve_links()
        return stored

    # --- maintenance --------------------------------------------------------

    def reconcile(self) -> ReconcileReport:
        """Heal the index against the filesystem.

        Notes are matched by their ``id`` alias when present, else by path; a
        size/mtime/path difference triggers a re-index. Index rows with no
        matching file are dropped. Identity is the surrogate ``noteid``.
        """
        indexed = 0
        rows = list(self.index.all_rows())  # (noteid, id, path, size, mtime, deleted_at)
        by_id = {row[1]: row for row in rows if row[1] is not None}
        by_path = {row[2]: row for row in rows}
        seen: set[int] = set()

        def match(note: Note) -> tuple[int, str | None, str, int, float, str | None] | None:
            return by_id.get(note.id) if note.id is not None else by_path.get(note.path)

        for note in self.store.iter_notes():
            abs_path = self.settings.vault_path / note.path
            size, mtime = self.store.stat(abs_path)
            row = match(note)
            if row is not None and row[5] is None and row[2] == note.path and not _changed(
                row, size, mtime
            ):
                seen.add(row[0])
            else:
                etag = self.store.content_hash(abs_path)
                seen.add(self.index.upsert(note, size=size, mtime=mtime, etag=etag))
                indexed += 1

        for note in self.store.iter_trash():
            abs_path = self.settings.vault_path / note.path
            size, mtime = self.store.stat(abs_path)
            deleted_at = datetime.fromtimestamp(mtime, tz=UTC)
            row = match(note)
            if row is not None and row[5] is not None and row[2] == note.path and not _changed(
                row, size, mtime
            ):
                seen.add(row[0])
            else:
                etag = self.store.content_hash(abs_path)
                seen.add(
                    self.index.upsert(
                        note, size=size, mtime=mtime, etag=etag, deleted_at=deleted_at
                    )
                )
                indexed += 1

        removed = 0
        for row in rows:
            if row[0] not in seen:
                self.index.remove_noteid(row[0])
                removed += 1
        self.index.resolve_links()
        return ReconcileReport(indexed=indexed, removed=removed)

    def reindex(self) -> ReindexReport:
        """Drop and rebuild the index from the filesystem."""
        self.index.clear()
        live = 0
        for note in self.store.iter_notes():
            abs_path = self.settings.vault_path / note.path
            size, mtime = self.store.stat(abs_path)
            self.index.upsert(
                note, size=size, mtime=mtime, etag=self.store.content_hash(abs_path)
            )
            live += 1
        trash = 0
        for note in self.store.iter_trash():
            abs_path = self.settings.vault_path / note.path
            size, mtime = self.store.stat(abs_path)
            self.index.upsert(
                note,
                size=size,
                mtime=mtime,
                etag=self.store.content_hash(abs_path),
                deleted_at=datetime.fromtimestamp(mtime, tz=UTC),
            )
            trash += 1
        self.index.resolve_links()
        return ReindexReport(live=live, trash=trash)


def _changed(
    row: tuple[int, str | None, str, int, float, str | None], size: int, mtime: float
) -> bool:
    return row[3] != size or abs(row[4] - mtime) > 1e-6


class LinkService:
    """Imports a remote URL into the vault by composing
    :func:`fetch_and_extract` with :meth:`NoteService.create`. Vault and index
    writes are owned entirely by ``NoteService``.
    """

    def __init__(
        self,
        note_service: NoteService,
        *,
        fetch_settings: LinkFetchSettings | None = None,
    ) -> None:
        self.note_service = note_service
        self.fetch_settings = fetch_settings or LinkFetchSettings()

    async def create_from_link(
        self,
        *,
        url: str,
        tags: list[str] | None = None,
        title_override: str | None = None,
        idempotency_key: str | None = None,
    ) -> tuple[Note, bool]:
        article = await fetch_and_extract(url, settings=self.fetch_settings)
        key = idempotency_key or _link_idempotency_key(url)
        title = (title_override or "").strip() or article.title or url
        return self.note_service.create(
            NoteCreate(
                title=title,
                body=article.markdown,
                tags=list(tags or []),
                source_url=article.final_url,
                idempotency_key=key,
            )
        )


def _link_idempotency_key(url: str) -> str:
    return "link:" + sha256(url.encode("utf-8")).hexdigest()[:16]
