"""Bartleby vault core: models, storage, search index, and service layer.

The filesystem (Markdown + YAML frontmatter) is the source of truth; a rebuildable
SQLite FTS5 index accelerates search. ``NoteService`` is the only surface that
higher layers (REST, MCP) should depend on. This package imports no web framework.
"""

__version__ = "0.1.0"
