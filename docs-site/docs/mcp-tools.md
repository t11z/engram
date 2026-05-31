# MCP tool reference

Engram exposes five MCP tools at `/mcp` (Streamable HTTP). All operate on the
same vault as the REST API. Authenticate with your `ENGRAM_AUTH_TOKEN` via your
client's standard MCP auth mechanism (sent as `Authorization: Bearer`). To connect
from claude.ai (Web), which requires OAuth instead of a static token, enable the
embedded OAuth server — see
[Configuration → OAuth for claude.ai](configuration.md#oauth-for-claudeai-optional).

The tool descriptions below are written for LLM consumption and mirror what the
running server advertises.

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
