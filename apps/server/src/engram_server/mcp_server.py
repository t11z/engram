"""The MCP tools and a factory that builds a fresh ``FastMCP`` per app.

A new instance per ``create_app`` avoids the streamable-HTTP session manager's
run-once constraint (so the app can be built more than once in a process, e.g.
across tests). Each tool is a thin call into the shared ``NoteService``;
docstrings are written for LLM consumption (they become the tool descriptions).
"""

from __future__ import annotations

import base64
import json

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


def get_backlinks(path: str) -> list[dict[str, object]]:
    """List notes that link to the note at `path` (its backlinks). Use this to see
    what references a note. Example: get_backlinks(path='projects/engram.md')."""
    return [
        {"path": s.path, "title": s.title, "tags": s.tags}
        for s in get_service().get_backlinks(path)
    ]


def get_links(path: str) -> list[dict[str, object]]:
    """List the outgoing links from the note at `path`. Each has the raw `target`,
    its `type` (wikilink/embed/markdown), and `resolved_path` (null if the link is
    dangling). Example: get_links(path='index.md')."""
    return [
        {"target": link.target, "type": link.type, "resolved_path": link.resolved_path}
        for link in get_service().get_outgoing_links(path)
    ]


def get_related(path: str) -> list[dict[str, object]]:
    """List notes one hop from `path` (its backlinks and resolved outgoing targets).
    Use this to explore a note's neighbourhood. Example: get_related(path='moc.md')."""
    return [
        {"path": s.path, "title": s.title, "tags": s.tags}
        for s in get_service().get_related(path)
    ]


def get_graph(path: str, depth: int = 1) -> dict[str, object]:
    """Return the link graph around `path` out to `depth` hops as `nodes` and
    `edges`. Use this to understand how a cluster of notes connects.
    Example: get_graph(path='moc.md', depth=2)."""
    graph = get_service().get_graph(path, depth=depth)
    return {
        "focus": graph.focus,
        "nodes": [{"path": n.path, "title": n.title} for n in graph.nodes],
        "edges": [{"source": e.source, "target": e.target, "type": e.type} for e in graph.edges],
    }


def list_folders() -> list[str]:
    """List the folders that contain notes. Use this to browse the vault's
    structure. Example: list_folders()."""
    return get_service().list_folders()


def list_tags() -> list[dict[str, object]]:
    """List every tag in the vault (frontmatter and inline `#tags`) with how many
    notes carry it. Use this to discover topics. Example: list_tags()."""
    return [{"tag": t.tag, "count": t.count} for t in get_service().list_tags()]


def get_note_by_title(title: str) -> dict[str, object]:
    """Read a note in full by its exact `title` (most recently updated wins).
    Example: get_note_by_title(title='Postgres backup command')."""
    note = get_service().get_by_title(title)
    return {"path": note.path, "title": note.title, "tags": note.tags, "body": note.body}


def update_note(
    path: str,
    title: str | None = None,
    body: str | None = None,
    tags: list[str] | None = None,
    expected_etag: str | None = None,
) -> dict[str, object]:
    """Replace a note's `title`, `body`, and/or `tags` (whichever you pass). Pass
    `expected_etag` (from a prior read) to fail safely if the note changed since.
    Example: update_note(path='todo.md', body='# Todo\\n- [x] ship')."""
    note = get_service().update_note(
        path, title=title, body=body, tags=tags, expected_etag=expected_etag
    )
    return {"path": note.path, "title": note.title}


def append_to_note(path: str, text: str) -> dict[str, object]:
    """Append a Markdown block to the end of a note's body. Safe to retry.
    Example: append_to_note(path='journal.md', text='- met with team')."""
    note = get_service().append_to_note(path, text)
    return {"path": note.path}


def patch_section(path: str, heading: str, content: str) -> dict[str, object]:
    """Replace the section under `heading` with `content` (the section is created
    if it doesn't exist). Use this to update one part of a note without rewriting
    it. Example: patch_section(path='notes.md', heading='Status', content='Done.')."""
    note = get_service().patch_section(path, heading, content)
    return {"path": note.path}


def list_attachments() -> list[dict[str, object]]:
    """List non-Markdown files in the vault (images, PDFs, …) with size and type.
    Use this to find a note's attachments. Example: list_attachments()."""
    return [
        {"path": a.path, "size": a.size, "content_type": a.content_type}
        for a in get_service().list_attachments()
    ]


def read_attachment(path: str) -> dict[str, object]:
    """Read an attachment's bytes by `path`, returned base64-encoded along with its
    content type. Example: read_attachment(path='attachments/diagram.png')."""
    data, content_type = get_service().read_attachment(path)
    return {"path": path, "content_type": content_type, "base64": base64.b64encode(data).decode()}


def append_to_daily_note(text: str) -> dict[str, object]:
    """Append a Markdown block to today's daily note (created if needed). Use this
    to jot something dated. Example: append_to_daily_note(text='- shipped the release')."""
    note = get_service().append_to_daily_note(text)
    return {"path": note.path}


def note_resource(path: str) -> str:
    """MCP resource: the full Markdown body of the note at `path`."""
    return get_service().get(path).body


def notes_resource() -> str:
    """MCP resource: a JSON list of the most recent notes (path + title + tags)."""
    items, _ = get_service().list_notes(limit=50)
    return json.dumps([{"path": s.path, "title": s.title, "tags": s.tags} for s in items])


def summarize_note(path: str) -> str:
    """Prompt: summarise a single note."""
    return (
        f"Read the note at `{path}` with the read_note tool, then summarise it in "
        f"3-5 concise bullet points, preserving any decisions or action items."
    )


def find_related(path: str) -> str:
    """Prompt: explore a note's connections."""
    return (
        f"Use get_related and get_backlinks for `{path}` to gather connected notes, "
        f"then explain in a short paragraph how they relate and what threads they share."
    )


def daily_review() -> str:
    """Prompt: review recent notes."""
    return (
        "Use list_notes to fetch the most recent notes, then write a brief review: "
        "what changed, open threads, and suggested next actions."
    )


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
    for tool in (
        save_note,
        search_notes,
        read_note,
        list_notes,
        delete_note,
        get_backlinks,
        get_links,
        get_related,
        get_graph,
        list_folders,
        list_tags,
        get_note_by_title,
        update_note,
        append_to_note,
        patch_section,
        list_attachments,
        read_attachment,
        append_to_daily_note,
    ):
        mcp.tool()(tool)
    mcp.resource("engram://note/{path}")(note_resource)
    mcp.resource("engram://notes")(notes_resource)
    for prompt in (summarize_note, find_related, daily_review):
        mcp.prompt()(prompt)
    return mcp
