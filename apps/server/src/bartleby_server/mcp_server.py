"""The MCP server and its five tools. Each tool is a thin call into the shared
``NoteService``; docstrings are written for LLM consumption (they become the tool
descriptions). Tools return plain JSON-serializable data.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from bartleby_core import NoteCreate

from .service import get_service

# streamable_http_path="/" so that, mounted at "/mcp", the endpoint is exactly
# "/mcp" (not "/mcp/mcp"). DNS-rebinding host/origin checks are disabled because
# the endpoint is bearer-authenticated and deployed behind the user's reverse
# proxy at an arbitrary host, which the default allowlist would reject.
mcp = FastMCP(
    "Bartleby",
    json_response=True,
    streamable_http_path="/",
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)


@mcp.tool()
def save_note(
    title: str,
    body: str,
    tags: list[str] | None = None,
    source_url: str | None = None,
    idempotency_key: str | None = None,
) -> dict[str, str]:
    """Save a new note to the vault. Use this to remember something for later: a
    fact, a snippet, a link, a decision. Provide a short `title` and the `body` as
    Markdown; add `tags` to make it findable. Returns the note's `id`.
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
    return {"id": note.id}


@mcp.tool()
def search_notes(query: str, tag: str | None = None, limit: int = 20) -> list[dict[str, object]]:
    """Search the vault by keyword and return the best matches with a snippet and
    id. Use this before answering from memory, to ground your answer in what the
    user actually saved. Example: search_notes(query='postgres backup')."""
    return [
        {"id": r.id, "title": r.title, "snippet": r.snippet, "score": r.score}
        for r in get_service().search(query, tag=tag, limit=limit)
    ]


@mcp.tool()
def read_note(id: str) -> dict[str, object]:
    """Read one note in full by its `id` (get the id from `search_notes` or
    `list_notes`). Returns the title, tags, and full Markdown body.
    Example: read_note(id='01J…')."""
    note = get_service().get(id)
    return {"id": note.id, "title": note.title, "tags": note.tags, "body": note.body}


@mcp.tool()
def list_notes(tag: str | None = None, limit: int = 20) -> list[dict[str, object]]:
    """List recent notes (newest first) as id + title + tags, optionally filtered
    by `tag`. Use this to browse what exists when you don't have a search term.
    Example: list_notes(tag='ops', limit=20)."""
    items, _ = get_service().list_notes(tag=tag, limit=limit)
    return [{"id": s.id, "title": s.title, "tags": s.tags} for s in items]


@mcp.tool()
def delete_note(id: str) -> dict[str, str]:
    """Move a note to the trash by `id` (soft-delete; it can be restored for 30
    days). Confirm with the user before deleting. Example: delete_note(id='01J…')."""
    get_service().delete(id)
    return {"id": id, "status": "deleted"}
