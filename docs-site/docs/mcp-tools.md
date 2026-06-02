# MCP reference

Engram exposes MCP **tools**, **resources**, and **prompts** at `/mcp`
(Streamable HTTP). All operate on the same vault as the REST API. Authenticate
with your `ENGRAM_AUTH_TOKEN` via your client's standard MCP auth mechanism (sent
as `Authorization: Bearer`). To connect from claude.ai (Web), which requires
OAuth instead of a static token, enable the embedded OAuth server — see
[Configuration → OAuth for claude.ai](configuration.md#oauth-for-claudeai-optional).

Notes are addressed by their **vault-relative path** (the canonical handle), not
by an id. The tool descriptions below are written for LLM consumption and mirror
what the running server advertises.

## Tools

### Notes

#### `save_note`

Save a new note to the vault — a fact, a snippet, a link, a decision. Provide the
`body` as Markdown and an optional short `title`; add `tags` to make it findable.
Returns the note's `path`.

```
save_note(title="Postgres backup cmd", body="`pg_dump …`", tags=["ops","postgres"])
```

#### `read_note`

Read one note in full **by its `path`** (obtained from `search_notes` or
`list_notes`). Returns title, tags, and the full Markdown body.

```
read_note(path="ops/postgres-backup-cmd.md")
```

#### `get_note_by_title`

Read a note by its exact title when you don't know its path.

```
get_note_by_title(title="Postgres backup cmd")
```

#### `list_notes`

List recent notes (newest first) as path + title + tags, optionally filtered by
`tag`. Use this to browse when you don't have a search term.

```
list_notes(tag="ops", limit=20)
```

#### `update_note`

Replace a note's body in place by `path`. Use this to revise an existing note
rather than creating a duplicate.

```
update_note(path="ops/postgres-backup-cmd.md", body="updated Markdown …")
```

#### `append_to_note`

Append text to the end of an existing note by `path`.

```
append_to_note(path="ops/postgres-backup-cmd.md", text="\n- also: --jobs=4")
```

#### `patch_section`

Replace the content under a given heading in a note, leaving the rest untouched.

```
patch_section(path="ops/runbook.md", heading="Rollback", content="1. …")
```

#### `append_to_daily_note`

Append text to today's daily note (created if needed, in the configured
daily-note folder).

```
append_to_daily_note(text="- shipped the v2 docs")
```

#### `delete_note`

Move a note to the trash **by `path`** (soft-delete; restorable for 30 days).
Confirm with the user before deleting.

```
delete_note(path="ops/postgres-backup-cmd.md")
```

### Search & graph

#### `search_notes`

Search the vault by keyword and return the best matches with a snippet and path.
Use this before answering from memory, to ground answers in what was actually
saved.

```
search_notes(query="postgres backup")
```

#### `get_backlinks`

List the notes that link to a given note (by `path`).

```
get_backlinks(path="ops/postgres-backup-cmd.md")
```

#### `get_links`

List the outbound links from a note (wikilinks, embeds, and Markdown links).

```
get_links(path="ops/runbook.md")
```

#### `get_related`

List notes related to a given note via the link graph.

```
get_related(path="ops/runbook.md")
```

#### `get_graph`

Return the link neighbourhood around a note out to a given depth.

```
get_graph(path="ops/runbook.md", depth=2)
```

#### `list_folders`

List the folders present in the vault.

```
list_folders()
```

#### `list_tags`

List the tags in the vault (the union of frontmatter and inline `#tags`).

```
list_tags()
```

### Attachments

#### `list_attachments`

List the files in the configured attachment store.

```
list_attachments()
```

#### `read_attachment`

Read an attachment's bytes by `path`.

```
read_attachment(path="attachments/diagram.png")
```

## Resources

- `engram://note/{path}` — a single note addressed by its vault-relative path.
- `engram://notes` — the collection of notes in the vault.

## Prompts

- `summarize_note` — summarize a note.
- `find_related` — find notes related to a given note.
- `daily_review` — review recent activity / the daily note.

## Testing

Use the [MCP Inspector](https://github.com/modelcontextprotocol/inspector) to
explore the tools, resources, and prompts against a running server:

```bash
npx @modelcontextprotocol/inspector
```
