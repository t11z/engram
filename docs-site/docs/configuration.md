# Configuration

Bartleby is configured entirely through environment variables (see
`infra/.env.example`). Only `BARTLEBY_AUTH_TOKEN` is required.

| Variable | Default | Description |
|----------|---------|-------------|
| `BARTLEBY_AUTH_TOKEN` | *(required)* | Bearer token shared by the REST API and MCP endpoint. Use a long random secret (`openssl rand -hex 32`). The server refuses to start without it. |
| `BARTLEBY_VAULT_PATH` | `/data/vault` | Directory where notes are stored on disk. |
| `BARTLEBY_HOST` | `0.0.0.0` | Bind address. |
| `BARTLEBY_PORT` | `8080` | Bind port. |
| `BARTLEBY_TRASH_RETENTION_DAYS` | `30` | Days a soft-deleted note stays in `.trash/` before being purged. |
| `BARTLEBY_INDEX_PATH` | `<vault>/.bartleby/index.db` | SQLite FTS5 search-index location. The index is a rebuildable cache, not your data. |
| `BARTLEBY_CORS_ORIGINS` | *(empty)* | Comma-separated allowed origins for the extension and web UI. Example: `chrome-extension://<id>,https://bartleby.example.com`. |
| `BARTLEBY_LOG_LEVEL` | `info` | `debug` \| `info` \| `warning` \| `error`. |

## Notes on the vault

- The vault is just Markdown files with YAML frontmatter. Back it up like any
  directory; edit it with any editor when the server is stopped.
- `.trash/` holds soft-deleted notes until the retention purge.
- `.bartleby/` holds the search index. Deleting it is safe — it rebuilds from
  your files on the next start.

## Notes on the token

The same token authenticates REST and MCP. It is never logged and the server
makes no outbound calls with it. Rotate it by changing the env var and
restarting; clients must be updated to match.
