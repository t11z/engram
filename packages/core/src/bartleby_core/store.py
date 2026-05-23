"""``VaultStore``: the filesystem source of truth.

Notes are flat Markdown files in the vault root, named ``YYYY-MM-DD-<slug>.md``.
This layer owns filename assignment, atomic writes, and id<->path resolution. It
knows nothing about the search index. Writes are serialized by an in-process lock
(single-user assumption).
"""

from __future__ import annotations

import threading
from collections.abc import Iterator
from pathlib import Path

from .errors import InvalidNote, NoteNotFound
from .frontmatter import read_note_file, write_note_file
from .models import Note
from .slug import build_filename, short_suffix, slugify


class VaultStore:
    def __init__(self, vault_path: Path) -> None:
        self.vault_path = vault_path
        self.lock = threading.Lock()

    @property
    def trash_dir(self) -> Path:
        return self.vault_path / ".trash"

    def ensure_layout(self) -> None:
        self.vault_path.mkdir(parents=True, exist_ok=True)
        self.trash_dir.mkdir(parents=True, exist_ok=True)

    # --- live notes ---------------------------------------------------------

    def write(self, note: Note) -> Note:
        """Write a note, assigning/refreshing its filename. Returns the stored note."""
        with self.lock:
            filename = self._assign_filename(note)
            previous = self._path_for_id(note.id)
            stored = note.model_copy(update={"path": filename})
            write_note_file(self.vault_path / filename, stored)
            if previous is not None and previous.name != filename:
                previous.unlink(missing_ok=True)
            return stored

    def read(self, note_id: str) -> Note:
        path = self._path_for_id(note_id)
        if path is None:
            raise NoteNotFound(note_id)
        return read_note_file(path, path.name)

    def exists(self, note_id: str) -> bool:
        return self._path_for_id(note_id) is not None

    def iter_notes(self) -> Iterator[Note]:
        for path in self._iter_live_paths():
            try:
                yield read_note_file(path, path.name)
            except InvalidNote:
                continue

    def path_for_id(self, note_id: str) -> Path | None:
        return self._path_for_id(note_id)

    @staticmethod
    def stat(abs_path: Path) -> tuple[int, float]:
        st = abs_path.stat()
        return st.st_size, st.st_mtime

    # --- internals ----------------------------------------------------------

    def _iter_live_paths(self) -> Iterator[Path]:
        if not self.vault_path.exists():
            return
        yield from sorted(self.vault_path.glob("*.md"))

    def _path_for_id(self, note_id: str) -> Path | None:
        for path in self._iter_live_paths():
            try:
                note = read_note_file(path, path.name)
            except InvalidNote:
                continue
            if note.id == note_id:
                return path
        return None

    def _assign_filename(self, note: Note) -> str:
        slug = slugify(note.title)
        candidate = build_filename(note.created_at, slug)
        if not self._name_taken(candidate, note.id):
            return candidate
        suffix = short_suffix(note.id)
        candidate = build_filename(note.created_at, slug, suffix)
        if not self._name_taken(candidate, note.id):
            return candidate
        counter = 2
        while True:
            candidate = build_filename(note.created_at, slug, f"{suffix}-{counter}")
            if not self._name_taken(candidate, note.id):
                return candidate
            counter += 1

    def _name_taken(self, filename: str, own_id: str) -> bool:
        path = self.vault_path / filename
        if not path.exists():
            return False
        try:
            existing = read_note_file(path, filename)
        except InvalidNote:
            return True
        return existing.id != own_id
