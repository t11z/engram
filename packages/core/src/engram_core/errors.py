"""Domain exceptions. The web layer (later phases) maps these to HTTP responses.

Nothing here imports a web framework.
"""

from __future__ import annotations


class EngramError(Exception):
    """Base class for all Engram domain errors."""


class NoteNotFound(EngramError):
    """No live note exists with the given id."""

    def __init__(self, note_id: str) -> None:
        self.note_id = note_id
        super().__init__(f"No note with id {note_id!r}.")


class NoteNotInTrash(EngramError):
    """The note to restore is not in the trash."""

    def __init__(self, note_id: str) -> None:
        self.note_id = note_id
        super().__init__(f"No trashed note with id {note_id!r}.")


class NoteAlreadyExists(EngramError):
    """A note with the given id already exists (ULID collision; effectively never)."""

    def __init__(self, note_id: str) -> None:
        self.note_id = note_id
        super().__init__(f"A note with id {note_id!r} already exists.")


class VaultError(EngramError):
    """A filesystem-level vault failure."""


class IndexUnavailable(EngramError):
    """The SQLite build lacks FTS5 support, so the search index cannot be opened."""


class InvalidNote(EngramError):
    """A note file could not be parsed or failed validation."""

    def __init__(self, path: str, reason: str) -> None:
        self.path = path
        self.reason = reason
        super().__init__(f"Invalid note {path!r}: {reason}")


class LinkFetchError(EngramError):
    """Base class for failures while importing a remote URL into the vault."""


class BlockedHost(LinkFetchError):
    """The requested URL targets a non-public host (loopback/private/reserved)
    or uses a disallowed scheme. Refused before any outbound request.
    """


class LinkUnreachable(LinkFetchError):
    """The remote host could not be reached, or returned a non-2xx response,
    or supplied an invalid redirect.
    """


class LinkTimeout(LinkFetchError):
    """The fetch exceeded the configured timeout."""


class LinkTooLarge(LinkFetchError):
    """The response body exceeded the configured byte cap."""


class UnsupportedContentType(LinkFetchError):
    """The response was not HTML (or a configured variant)."""


class LinkExtractionFailed(LinkFetchError):
    """The page was fetched but no article-like content could be extracted."""
