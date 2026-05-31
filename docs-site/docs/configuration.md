# Configuration

Engram is configured entirely through environment variables (see
`infra/.env.example`). Only `ENGRAM_AUTH_TOKEN` is required.

| Variable | Default | Description |
|----------|---------|-------------|
| `ENGRAM_AUTH_TOKEN` | *(required)* | Bearer token shared by the REST API and MCP endpoint. Use a long random secret (`openssl rand -hex 32`). The server refuses to start without it. |
| `ENGRAM_VAULT_PATH` | `/data/vault` | Directory where notes are stored on disk. |
| `ENGRAM_HOST` | `0.0.0.0` | Bind address. |
| `ENGRAM_PORT` | `8080` | Bind port. |
| `ENGRAM_TRASH_RETENTION_DAYS` | `30` | Days a soft-deleted note stays in `.trash/` before being purged. |
| `ENGRAM_INDEX_PATH` | `<vault>/.engram/index.db` | SQLite FTS5 search-index location. The index is a rebuildable cache, not your data. |
| `ENGRAM_CORS_ORIGINS` | *(empty)* | Comma-separated allowed origins for the extension and web UI. Example: `chrome-extension://<id>,https://engram.example.com`. |
| `ENGRAM_PUBLIC_URL` | *(empty)* | Public HTTPS origin where the server is reachable (no trailing path). Setting it enables the embedded OAuth server and becomes the token issuer / resource identifier. Required to connect from claude.ai. |
| `ENGRAM_OAUTH_PASSWORD` | *(empty)* | Password for the OAuth login/consent page. Required whenever `ENGRAM_PUBLIC_URL` is set; the server refuses to start otherwise. |
| `ENGRAM_LOG_LEVEL` | `info` | `debug` \| `info` \| `warning` \| `error`. |

## Notes on the vault

- The vault is just Markdown files with YAML frontmatter. Back it up like any
  directory; edit it with any editor when the server is stopped.
- `.trash/` holds soft-deleted notes until the retention purge.
- `.engram/` holds the search index. Deleting it is safe — it rebuilds from
  your files on the next start.

## Notes on the token

The same token authenticates REST and MCP. It is never logged and the server
makes no outbound calls with it. Rotate it by changing the env var and
restarting; clients must be updated to match.

## OAuth for claude.ai (optional)

claude.ai (Web) adds remote MCP servers only through the OAuth flow — it cannot
store a static bearer token. Set **both** `ENGRAM_PUBLIC_URL` (your public HTTPS
origin) and `ENGRAM_OAUTH_PASSWORD` to turn on Engram's embedded OAuth 2.1
authorization server. Then in claude.ai → **Settings → Connectors → Add custom
connector**, paste your `https://<host>/mcp` URL; claude.ai registers itself
automatically and walks you through a login page where you enter the OAuth
password.

- `ENGRAM_PUBLIC_URL` is the OAuth **issuer** and resource identifier. It must
  be HTTPS in production (localhost HTTP is allowed only for local testing) and
  must match the URL clients actually reach — the server uses it directly instead
  of guessing from proxy headers. Terminate TLS at your reverse proxy (see the
  Caddy example in `infra/`).
- `ENGRAM_OAUTH_PASSWORD` gates the consent page. Dynamic Client Registration
  is open by design, so without this password anyone who can reach the public URL
  could obtain a token. Use a long random secret.
- The static `ENGRAM_AUTH_TOKEN` keeps working everywhere. When OAuth is on,
  `/mcp` accepts **either** an OAuth access token **or** the static token, so the
  web UI, browser extension, MCP Inspector, and Claude Desktop are unaffected.
- Registered OAuth clients and issued tokens are stored in
  `<vault>/.engram/oauth.db`. Unlike the search index, this database is **not**
  rebuildable and holds secrets — back it up and protect it together with the
  vault. Deleting it forces every OAuth client (including claude.ai) to
  re-authorize.
- Access tokens expire after about an hour; refresh tokens last ~30 days and
  rotate on use. To revoke access immediately, the client can call the
  revocation endpoint, or you can stop the server and remove `oauth.db`.

When `ENGRAM_PUBLIC_URL` is unset, none of this is active and the server runs
exactly as it did before — static-token auth only.
