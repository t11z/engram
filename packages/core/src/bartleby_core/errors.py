"""Domain exceptions. The web layer (later phases) maps these to HTTP responses.

Nothing here imports a web framework.
"""

from __future__ import annotations


class BartlebyError(Exception):
    """Base class for all Bartleby domain errors."""


class NoteNotFound(BartlebyError):
    """No live note exists with the given id."""

    def __init__(self, note_id: str) -> None:
        self.note_id = note_id
        super().__init__(f"No note with id {note_id!r}.")


class NoteNotInTrash(BartlebyError):
    """The note to restore is not in the trash."""

    def __init__(self, note_id: str) -> None:
        self.note_id = note_id
        super().__init__(f"No trashed note with id {note_id!r}.")


class NoteAlreadyExists(BartlebyError):
    """A note with the given id already exists (ULID collision; effectively never)."""

    def __init__(self, note_id: str) -> None:
        self.note_id = note_id
        super().__init__(f"A note with id {note_id!r} already exists.")


class VaultError(BartlebyError):
    """A filesystem-level vault failure."""


class IndexUnavailable(BartlebyError):
    """The SQLite build lacks FTS5 support, so the search index cannot be opened."""


class InvalidNote(BartlebyError):
    """A note file could not be parsed or failed validation."""

    def __init__(self, path: str, reason: str) -> None:
        self.path = path
        self.reason = reason
        super().__init__(f"Invalid note {path!r}: {reason}")
