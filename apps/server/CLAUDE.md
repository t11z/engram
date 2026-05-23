# CLAUDE.md — server

Working manual for `apps/server` (FastAPI: REST + MCP + static UI). Architecture
is in [`/docs/IMPLEMENTATION_PLAN.md`](../../docs/IMPLEMENTATION_PLAN.md); keep
this practical.

> The server is thin. All note logic lives in `packages/core`. Handlers
> validate input, call a `core` service, and shape the response — nothing more.

## Run locally against the sample vault

```bash
BARTLEBY_VAULT_PATH=../../packages/core/tests/fixtures/sample-vault \
BARTLEBY_AUTH_TOKEN=dev \
uv run bartleby
```

REST at `http://localhost:8080/api/v1`, MCP at `/mcp`, UI at `/`. Health at
`/healthz` (no auth).

## Add a new MCP tool

1. Define the handler in the MCP module and register it with the
   `mcp.server.fastmcp` app. It must call a `packages/core` service — no storage
   logic in the tool.
2. **Write the description for an LLM**, not a human reader. Be concise and
   action-oriented, say *when* to use it, and include one example call. Follow
   the five existing tools as the template (see the API section of the plan).
3. Add a test that exercises the tool through the MCP layer.
4. **Verify with MCP Inspector**:
   ```bash
   npx @modelcontextprotocol/inspector
   ```
   Connect to `http://localhost:8080/mcp` with the bearer token, confirm the tool
   lists, the schema is right, and a call round-trips.

## Add a new REST endpoint

1. Add the route under the `/api/v1` router; use `packages/core` models for
   request/response so the schema is generated, not hand-written.
2. Call a `core` service; keep the handler thin.
3. **Regenerate the contract** and commit it (CI fails on drift):
   the OpenAPI schema + TS types in `packages/contract`.
4. **Versioning**: additive changes stay in `/api/v1`. Bump the version only for
   a breaking change, and record the reason in an ADR.
5. Add tests (happy path + auth failure + not-found).

## Storage layer

`packages/core` owns it behind a `VaultStore`: Markdown + YAML frontmatter is the
source of truth; a rebuildable SQLite FTS5 index (default `<vault>/.bartleby/index.db`)
accelerates search via write-through + startup reconciliation + `reindex`. The
server never touches the index directly — go through a `core` service.

## Tests

Live in `apps/server/tests/`. Use the sample vault under
`packages/core/tests/fixtures/sample-vault/` (copy to a tmp dir for tests that
write). Cover REST + MCP + auth.
