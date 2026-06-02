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
    NoteConflict,
    NoteNotFound,
    NoteNotInTrash,
    UnsupportedContentType,
    VaultError,
)
from .link_extractor import ExtractedArticle, LinkFetchSettings, fetch_and_extract
from .links import ParsedLink, extract_inline_tags, extract_links
from .models import (
    AttachmentInfo,
    GraphEdge,
    GraphNode,
    GraphView,
    Note,
    NoteCreate,
    NoteMeta,
    NoteSummary,
    OutgoingLink,
    SearchResult,
    TagCount,
)
from .service import LinkService, NoteService, ReconcileReport, ReindexReport
from .watcher import VaultWatcher

__version__ = "0.1.0"

__all__ = [
    "AttachmentInfo",
    "BlockedHost",
    "EngramError",
    "ExtractedArticle",
    "GraphEdge",
    "GraphNode",
    "GraphView",
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
    "NoteConflict",
    "NoteCreate",
    "NoteMeta",
    "NoteNotFound",
    "NoteNotInTrash",
    "NoteService",
    "NoteSummary",
    "OutgoingLink",
    "ParsedLink",
    "ReconcileReport",
    "ReindexReport",
    "SearchResult",
    "Settings",
    "TagCount",
    "UnsupportedContentType",
    "VaultError",
    "VaultWatcher",
    "__version__",
    "extract_inline_tags",
    "extract_links",
    "fetch_and_extract",
]
