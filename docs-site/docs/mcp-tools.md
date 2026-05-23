# MCP tool reference

!!! note "Hand-maintained for now"
    Until the server exists, this page is maintained by hand from the
    [implementation plan](https://github.com/t11z/bartleby/blob/main/docs/IMPLEMENTATION_PLAN.md).
    Once the MCP endpoint ships, it will be generated from the running server so
    descriptions never drift.

Bartleby exposes five MCP tools at `/mcp`. All operate on the same vault as the
REST API. Authenticate with your `BARTLEBY_AUTH_TOKEN` via your client's standard
MCP auth mechanism.

### `save_note`

Save a new note to the vault — a fact, a snippet, a link, a decision. Provide a
short `title` and the `body` as Markdown; add `tags` to make it findable. Returns
the note's `id`.

```
save_note(title="Postgres backup cmd", body="`pg_dump …`", tags=["ops","postgres"])
```

### `search_notes`

Search the vault by keyword and return the best matches with a snippet and id.
Use this before answering from memory, to ground answers in what was actually
saved.

```
search_notes(query="postgres backup")
```

### `read_note`

Read one note in full by its `id` (obtained from `search_notes` or
`list_notes`). Returns title, tags, and the full Markdown body.

```
read_note(id="01J…")
```

### `list_notes`

List recent notes (newest first) as id + title + tags, optionally filtered by
`tag`. Use this to browse when you don't have a search term.

```
list_notes(tag="ops", limit=20)
```

### `delete_note`

Move a note to the trash by `id` (soft-delete; restorable for 30 days). Confirm
with the user before deleting.

```
delete_note(id="01J…")
```

## Testing tools

Use the [MCP Inspector](https://github.com/modelcontextprotocol/inspector) to
explore the tools against a running server:

```bash
npx @modelcontextprotocol/inspector
```
