"""``VaultStore``: the filesystem source of truth.

Notes are Markdown files at any depth under the vault root; the vault-relative
path is a note's canonical handle. This layer owns filename assignment for new
notes, atomic writes, and path-based trash/restore. It knows nothing about the
search index. Writes are serialized by an in-process lock (single-user
assumption).
"""

from __future__ import annotations

import hashlib
import os
import threading
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

from .errors import InvalidNote, NoteNotFound, NoteNotInTrash
from .frontmatter import read_note_file, write_note_file
from .models import Note
from .slug import build_filename, slugify

TRASH = ".trash"
ENGRAM = ".engram"


class VaultStore:
    def __init__(self, vault_path: Path, new_note_dir: str = "") -> None:
        self.vault_path = vault_path
        self.new_note_dir = new_note_dir.strip("/")
        self.lock = threading.Lock()

    @property
    def trash_dir(self) -> Path:
        return self.vault_path / TRASH

    def ensure_layout(self) -> None:
        self.vault_path.mkdir(parents=True, exist_ok=True)
        self.trash_dir.mkdir(parents=True, exist_ok=True)

    # --- live notes ---------------------------------------------------------

    def write(self, note: Note) -> Note:
        """Write a note. New notes (empty path) get a title-derived filename;
        notes with a path are written there. Returns the stored note.
        """
        with self.lock:
            rel = note.path or self._assign_filename(note.title)
            abs_path = self.vault_path / rel
            stored = note.model_copy(update={"path": rel})
            write_note_file(abs_path, stored)
            return stored

    def read(self, rel_path: str) -> Note:
        abs_path = self.vault_path / rel_path
        if not abs_path.exists():
            raise NoteNotFound(rel_path)
        return read_note_file(abs_path, rel_path)

    def iter_notes(self) -> Iterator[Note]:
        for path in self._iter_live_paths():
            rel = path.relative_to(self.vault_path).as_posix()
            try:
                yield read_note_file(path, rel)
            except InvalidNote:
                continue

    def path_for_id(self, note_id: str) -> str | None:
        """Scan live notes for one whose frontmatter ``id`` matches (alias lookup)."""
        for path in self._iter_live_paths():
            rel = path.relative_to(self.vault_path).as_posix()
            try:
                note = read_note_file(path, rel)
            except InvalidNote:
                continue
            if note.id == note_id:
                return rel
        return None

    @staticmethod
    def stat(abs_path: Path) -> tuple[int, float]:
        st = abs_path.stat()
        return st.st_size, st.st_mtime

    # --- attachments --------------------------------------------------------

    def iter_attachments(self) -> Iterator[tuple[str, int]]:
        """Yield (relative path, size) for every non-Markdown file in the vault,
        skipping dotfolders (``.trash``, ``.engram``, editor config, …).
        """
        if not self.vault_path.exists():
            return
        for path in sorted(self.vault_path.rglob("*")):
            if not path.is_file() or path.suffix.lower() == ".md":
                continue
            rel = path.relative_to(self.vault_path)
            if any(part.startswith(".") for part in rel.parts):
                continue
            yield rel.as_posix(), path.stat().st_size

    def read_attachment(self, rel_path: str) -> bytes:
        """Read an attachment's bytes, refusing traversal, dotfolders, and notes."""
        norm = rel_path.strip("/")
        resolved = (self.vault_path / norm).resolve()
        try:
            rel = resolved.relative_to(self.vault_path.resolve())
        except ValueError as exc:
            raise NoteNotFound(rel_path) from exc
        if (
            any(part.startswith(".") for part in rel.parts)
            or rel.suffix.lower() == ".md"
            or not resolved.is_file()
        ):
            raise NoteNotFound(rel_path)
        return resolved.read_bytes()

    @staticmethod
    def content_hash(abs_path: Path) -> str:
        """SHA-256 of the file's bytes — the version token for optimistic
        concurrency (ADR-0009). Reflects the exact on-disk content, not engram's
        canonical serialization.
        """
        return hashlib.sha256(abs_path.read_bytes()).hexdigest()

    # --- trash --------------------------------------------------------------

    def move_to_trash(self, rel_path: str, now: datetime) -> str:
        """Soft-delete: move a live note into ``.trash/`` preserving its subpath.
        The trash file's mtime is set to ``now`` so deletion time is recoverable.
        Returns the trash-relative path (``.trash/<subpath>``).
        """
        with self.lock:
            src = self.vault_path / rel_path
            if not src.exists():
                raise NoteNotFound(rel_path)
            dest = self._free_path(self.trash_dir / rel_path)
            dest.parent.mkdir(parents=True, exist_ok=True)
            os.replace(src, dest)
            ts = now.timestamp()
            os.utime(dest, (ts, ts))
            return dest.relative_to(self.vault_path).as_posix()

    def restore(self, trash_rel_path: str) -> Note:
        """Restore a trashed note (``.trash/<subpath>``) back to its original
        location, resolving a name collision if one appeared meanwhile.
        """
        with self.lock:
            src = self.vault_path / trash_rel_path
            if not src.exists() or TRASH not in Path(trash_rel_path).parts:
                raise NoteNotInTrash(trash_rel_path)
            original = Path(trash_rel_path).relative_to(TRASH).as_posix()
            dest = self._free_path(self.vault_path / original)
            dest.parent.mkdir(parents=True, exist_ok=True)
            os.replace(src, dest)
            rel = dest.relative_to(self.vault_path).as_posix()
            return read_note_file(dest, rel)

    def iter_trash(self) -> Iterator[Note]:
        for path in self._iter_trash_paths():
            rel = path.relative_to(self.vault_path).as_posix()
            try:
                yield read_note_file(path, rel)
            except InvalidNote:
                continue

    def purge_expired(self, retention_days: int, now: datetime) -> list[str]:
        """Delete trash files whose deletion time (mtime) is older than retention.
        Returns the trash-relative paths that were purged.
        """
        cutoff = now - timedelta(days=retention_days)
        purged: list[str] = []
        with self.lock:
            for path in self._iter_trash_paths():
                deleted_at = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
                if deleted_at >= cutoff:
                    continue
                rel = path.relative_to(self.vault_path).as_posix()
                path.unlink(missing_ok=True)
                purged.append(rel)
        return purged

    # --- internals ----------------------------------------------------------

    def _iter_live_paths(self) -> Iterator[Path]:
        if not self.vault_path.exists():
            return
        for path in sorted(self.vault_path.rglob("*.md")):
            parts = path.relative_to(self.vault_path).parts
            if any(part.startswith(".") for part in parts):
                continue  # skip .trash/, .engram/, and other dotfolders
            yield path

    def _iter_trash_paths(self) -> Iterator[Path]:
        if not self.trash_dir.exists():
            return
        yield from sorted(self.trash_dir.rglob("*.md"))

    def _free_path(self, dest: Path) -> Path:
        """Return ``dest`` or, if taken, the same stem with a ``-N`` suffix."""
        if not dest.exists():
            return dest
        stem, parent = dest.stem, dest.parent
        counter = 2
        while True:
            candidate = parent / f"{stem}-{counter}.md"
            if not candidate.exists():
                return candidate
            counter += 1

    def _assign_filename(self, title: str) -> str:
        slug = slugify(title)
        folder = self.vault_path / self.new_note_dir if self.new_note_dir else self.vault_path
        dest = self._free_path(folder / build_filename(slug))
        return dest.relative_to(self.vault_path).as_posix()
