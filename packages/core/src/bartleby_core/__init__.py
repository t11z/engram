"""Bartleby vault core: models, storage, search index, and service layer.

The filesystem (Markdown + YAML frontmatter) is the source of truth; a rebuildable
SQLite FTS5 index accelerates search. ``NoteService`` is the only surface that
higher layers (REST, MCP) should depend on. This package imports no web framework.
"""

from .config import Settings
from .errors import (
    BartlebyError,
    IndexUnavailable,
    InvalidNote,
    NoteAlreadyExists,
    NoteNotFound,
    NoteNotInTrash,
    VaultError,
)
from .models import Note, NoteCreate, NoteMeta, NoteSummary, SearchResult
from .service import NoteService, ReconcileReport, ReindexReport

__version__ = "0.1.0"

__all__ = [
    "BartlebyError",
    "IndexUnavailable",
    "InvalidNote",
    "Note",
    "NoteAlreadyExists",
    "NoteCreate",
    "NoteMeta",
    "NoteNotFound",
    "NoteNotInTrash",
    "NoteService",
    "NoteSummary",
    "ReconcileReport",
    "ReindexReport",
    "SearchResult",
    "Settings",
    "VaultError",
    "__version__",
]
