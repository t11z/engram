"""``NoteService``: the public API that REST and MCP build on.

Composes the filesystem ``VaultStore`` (source of truth) and the ``SearchIndex``
(rebuildable cache), enforcing write-through ordering (file write is the commit
point, index follows) and idempotency. No web framework is imported here.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from .config import Settings
from .frontmatter import read_note_file
from .ids import new_ulid
from .index import SearchIndex
from .models import Note, NoteCreate, NoteSummary, SearchResult
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
        self.store = VaultStore(settings.vault_path)
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
            id=new_ulid(),
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
        size, mtime = self.store.stat(self.settings.vault_path / stored.path)
        self.index.upsert(stored, size=size, mtime=mtime)
        return stored, True

    def delete(self, note_id: str, *, now: datetime | None = None) -> None:
        """Soft-delete: move to trash and mark the index row trashed."""
        ts = now or datetime.now(UTC)
        note = self.get(note_id)  # raises NoteNotFound if not live
        dest = self.store.move_to_trash(note_id, ts)
        trashed = note.model_copy(update={"path": f".trash/{dest.name}"})
        size, mtime = self.store.stat(dest)
        self.index.upsert(trashed, size=size, mtime=mtime, deleted_at=ts)

    def restore(self, note_id: str) -> Note:
        note = self.store.restore(note_id)  # raises NoteNotInTrash
        size, mtime = self.store.stat(self.settings.vault_path / note.path)
        self.index.upsert(note, size=size, mtime=mtime)
        return note

    def purge_expired_trash(self, *, now: datetime | None = None) -> list[str]:
        ts = now or datetime.now(UTC)
        purged = self.store.purge_expired(self.settings.trash_retention_days, ts)
        for note_id in purged:
            self.index.remove(note_id)
        return purged

    # --- queries ------------------------------------------------------------

    def get(self, note_id: str) -> Note:
        path = self.index.get_path(note_id)
        if path is not None:
            abs_path = self.settings.vault_path / path
            if abs_path.exists():
                return read_note_file(abs_path, path)
        return self.store.read(note_id)  # raises NoteNotFound

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

    # --- maintenance --------------------------------------------------------

    def reconcile(self) -> ReconcileReport:
        """Heal the index against the filesystem using size/mtime comparison."""
        indexed = 0
        seen: set[str] = set()
        idx_rows = {row[0]: row for row in self.index.all_rows()}

        for note in self.store.iter_notes():
            seen.add(note.id)
            abs_path = self.settings.vault_path / note.path
            size, mtime = self.store.stat(abs_path)
            row = idx_rows.get(note.id)
            if row is None or row[4] is not None or _changed(row, size, mtime):
                self.index.upsert(note, size=size, mtime=mtime)
                indexed += 1

        for note in self.store.iter_trash():
            seen.add(note.id)
            abs_path = self.settings.vault_path / note.path
            size, mtime = self.store.stat(abs_path)
            deleted_at = datetime.fromtimestamp(mtime, tz=UTC)
            row = idx_rows.get(note.id)
            if row is None or row[4] is None or _changed(row, size, mtime):
                self.index.upsert(note, size=size, mtime=mtime, deleted_at=deleted_at)
                indexed += 1

        removed = 0
        for note_id in idx_rows:
            if note_id not in seen:
                self.index.remove(note_id)
                removed += 1
        return ReconcileReport(indexed=indexed, removed=removed)

    def reindex(self) -> ReindexReport:
        """Drop and rebuild the index from the filesystem."""
        self.index.clear()
        live = 0
        for note in self.store.iter_notes():
            size, mtime = self.store.stat(self.settings.vault_path / note.path)
            self.index.upsert(note, size=size, mtime=mtime)
            live += 1
        trash = 0
        for note in self.store.iter_trash():
            abs_path = self.settings.vault_path / note.path
            size, mtime = self.store.stat(abs_path)
            self.index.upsert(
                note, size=size, mtime=mtime, deleted_at=datetime.fromtimestamp(mtime, tz=UTC)
            )
            trash += 1
        return ReindexReport(live=live, trash=trash)


def _changed(row: tuple[str, str, int, float, str | None], size: int, mtime: float) -> bool:
    return row[2] != size or abs(row[3] - mtime) > 1e-6
