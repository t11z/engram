"""The MCP tools and a factory that builds a fresh ``FastMCP`` per app.

A new instance per ``create_app`` avoids the streamable-HTTP session manager's
run-once constraint (so the app can be built more than once in a process, e.g.
across tests). Each tool is a thin call into the shared ``NoteService``;
docstrings are written for LLM consumption (they become the tool descriptions).
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from engram_core import NoteCreate

from .service import get_service


def save_note(
    title: str,
    body: str,
    tags: list[str] | None = None,
    source_url: str | None = None,
    idempotency_key: str | None = None,
) -> dict[str, object]:
    """Save a new note to the vault. Use this to remember something for later: a
    fact, a snippet, a link, a decision. Provide a short `title` and the `body` as
    Markdown; add `tags` to make it findable. Returns the note's `path` (its handle).
    Example: save_note(title='Postgres backup cmd', body='`pg_dump …`', tags=['ops','postgres'])."""
    note, _ = get_service().create(
        NoteCreate(
            title=title,
            body=body,
            tags=tags or [],
            source_url=source_url,
            idempotency_key=idempotency_key,
        )
    )
    return {"path": note.path}


def search_notes(query: str, tag: str | None = None, limit: int = 20) -> list[dict[str, object]]:
    """Search the vault by keyword and return the best matches with a snippet and
    `path`. Use this before answering from memory, to ground your answer in what the
    user actually saved. Example: search_notes(query='postgres backup')."""
    return [
        {"path": r.path, "title": r.title, "snippet": r.snippet, "score": r.score}
        for r in get_service().search(query, tag=tag, limit=limit)
    ]


def read_note(path: str) -> dict[str, object]:
    """Read one note in full by its `path` (get the path from `search_notes` or
    `list_notes`). Returns the title, tags, and full Markdown body.
    Example: read_note(path='postgres-backup-cmd.md')."""
    note = get_service().get(path)
    return {"path": note.path, "title": note.title, "tags": note.tags, "body": note.body}


def list_notes(tag: str | None = None, limit: int = 20) -> list[dict[str, object]]:
    """List recent notes (newest first) as path + title + tags, optionally filtered
    by `tag`. Use this to browse what exists when you don't have a search term.
    Example: list_notes(tag='ops', limit=20)."""
    items, _ = get_service().list_notes(tag=tag, limit=limit)
    return [{"path": s.path, "title": s.title, "tags": s.tags} for s in items]


def delete_note(path: str) -> dict[str, str]:
    """Move a note to the trash by `path` (soft-delete; it can be restored for 30
    days). Confirm with the user before deleting. Example: delete_note(path='old-note.md')."""
    get_service().delete(path)
    return {"path": path, "status": "deleted"}


def build_mcp() -> FastMCP:
    """Construct a fresh MCP server with the five tools registered.

    ``streamable_http_path="/"`` makes the endpoint exactly ``/mcp`` once mounted.
    DNS-rebinding host/origin checks are disabled: the endpoint is
    bearer-authenticated and deployed behind the user's reverse proxy at an
    arbitrary host that the default allowlist would reject.
    """
    mcp = FastMCP(
        "Engram",
        json_response=True,
        streamable_http_path="/",
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    )
    mcp.tool()(save_note)
    mcp.tool()(search_notes)
    mcp.tool()(read_note)
    mcp.tool()(list_notes)
    mcp.tool()(delete_note)
    return mcp
