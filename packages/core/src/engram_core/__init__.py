"""Engram vault core: models, storage, search index, and service layer.

The filesystem (Markdown + YAML frontmatter) is the source of truth; a rebuildable
SQLite FTS5 index accelerates search. ``NoteService`` is the only surface that
higher layers (REST, MCP) should depend on. This package imports no web framework.
"""

from .config import Settings
from .errors import (
    BlockedHost,
    EngramError,
    IndexUnavailable,
    InvalidNote,
    LinkExtractionFailed,
    LinkFetchError,
    LinkTimeout,
    LinkTooLarge,
    LinkUnreachable,
    NoteAlreadyExists,
    NoteNotFound,
    NoteNotInTrash,
    UnsupportedContentType,
    VaultError,
)
from .link_extractor import ExtractedArticle, LinkFetchSettings, fetch_and_extract
from .models import Note, NoteCreate, NoteMeta, NoteSummary, SearchResult
from .service import LinkService, NoteService, ReconcileReport, ReindexReport

__version__ = "0.1.0"

__all__ = [
    "BlockedHost",
    "EngramError",
    "ExtractedArticle",
    "IndexUnavailable",
    "InvalidNote",
    "LinkExtractionFailed",
    "LinkFetchError",
    "LinkFetchSettings",
    "LinkService",
    "LinkTimeout",
    "LinkTooLarge",
    "LinkUnreachable",
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
    "UnsupportedContentType",
    "VaultError",
    "__version__",
    "fetch_and_extract",
]
