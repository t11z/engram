# Bartleby — Implementation Plan

This is the source of truth for Bartleby's architecture and delivery roadmap.
It records decisions so individual sessions and contributors do not re-litigate
them. Working conventions (how to branch, test, commit) live in `CLAUDE.md`, not
here. Individual decisions with trade-offs are captured as ADRs under
[`docs/adr/`](./adr/).

Status: **pre-implementation**. No application code exists yet. The next session
begins Phase 1 (core + storage).

---

## 1. Architecture summary

Bartleby is an LLM-agnostic, self-hosted personal knowledge vault. A single
backend process exposes three surfaces:

- `/mcp` — spec-compliant Model Context Protocol endpoint for LLM clients.
- `/api/v1/*` — versioned REST API for the browser extension and web UI.
- `/` — the static web UI bundle, served by the same process.

Decisions of record (not up for revision in v1):

- **Topology.** Public monorepo, MIT licensed, self-hosted per user. One user,
  one server, their own machine. No multi-tenancy, no accounts, no hosted demo.
- **Single process.** MCP, REST, and static UI are served by one FastAPI app.
  Rationale in [ADR-0002](./adr/0002-mcp-rest-coexist.md).
- **Storage.** Markdown files on disk with YAML frontmatter; the filesystem is
  the source of truth. A rebuildable SQLite FTS5 index accelerates search.
- **Auth.** A single bearer token (env var) shared by REST and MCP. No OAuth in v1.
- **Privacy.** The server makes no outbound calls. No telemetry, no update checks.
- **Soft-delete.** Delete moves notes to `.trash/`; a scheduled purge removes them
  after a configurable retention (default 30 days). Restore is supported.
- **Idempotency.** `POST /notes` accepts a client-supplied `idempotency_key`;
  repeated calls return the existing note.
- **Versioning.** All REST under `/api/v1/`. SemVer releases. `CHANGELOG.md` from
  day one (Keep a Changelog).
- **LLM-agnostic, Claude-validated.** Spec-compliant for any MCP client; tested
  primarily with Claude.

```mermaid
flowchart LR
  subgraph clients [Clients]
    L[LLM client - Claude / others]
    E[Browser extension]
    W[Web UI]
  end
  subgraph server [Bartleby server - one process]
    MCP[/mcp/]
    REST[/api/v1/*/]
    STATIC[/ static UI/]
    CORE[packages/core - services]
    IDX[(SQLite FTS5 index)]
  end
  V[(Vault: Markdown + YAML on disk)]

  L -->|MCP| MCP
  E -->|REST + bearer| REST
  W -->|REST + bearer| REST
  W -. served by .-> STATIC
  MCP --> CORE
  REST --> CORE
  CORE --> V
  CORE --> IDX
```

---

## 2. Repository layout

```
bartleby/
├── packages/
│   ├── core/            # Pydantic models + service layer (save/search/read/list/delete). No web framework imports.
│   └── contract/        # OpenAPI schema + generated TypeScript types, committed for clients to consume.
├── apps/
│   ├── server/          # FastAPI app: mounts REST, MCP, and the static UI. Calls into packages/core.
│   ├── web-ui/          # SvelteKit (static adapter) + Tailwind. Vault browser, read-only viewer, delete.
│   └── extension/       # Manifest V3 extension (Chrome + Firefox): clip tab to Markdown, POST to the server.
├── infra/               # Dockerfile, docker-compose, Caddy + systemd examples, .env.example.
├── docs/                # Markdown sources: this plan, ADRs.
│   └── adr/             # Architecture Decision Records.
├── docs-site/           # MkDocs Material site published to GitHub Pages.
├── .github/             # Issue/PR templates, workflows, dependabot.
└── .claude/             # Workflow automation (issue-first hook) + working state.
```

---

## 3. Data model

A **Note** is a Markdown file with a YAML frontmatter header. The filesystem is
canonical; everything else is derived.

### Frontmatter fields

| Field          | Type            | Required | Notes |
|----------------|-----------------|----------|-------|
| `id`           | string (ULID)   | yes      | Stable identity, assigned on create. Never changes. |
| `title`        | string          | yes      | Human title. Drives the filename slug but is independent of it. |
| `created_at`   | string (RFC 3339)| yes     | UTC timestamp. |
| `updated_at`   | string (RFC 3339)| yes     | UTC timestamp, bumped on every write. |
| `tags`         | list[string]    | no       | Free-form tags. Default `[]`. |
| `source_url`   | string          | no       | Origin URL when clipped by the extension. |
| `idempotency_key` | string       | no       | Client-supplied de-duplication key (see API). |

The Markdown body follows the frontmatter. The body is never parsed for meaning
in v1 — it is stored and returned verbatim.

### Pydantic models (`packages/core`)

- `NoteMeta` — the frontmatter fields above.
- `Note` — `NoteMeta` + `body: str` + `path: str` (relative to the vault root).
- `NoteCreate` — `title`, `body`, optional `tags`, `source_url`, `idempotency_key`.
- `NoteSummary` — `id`, `title`, `tags`, `updated_at`, `path` (list/search results, no body).
- `SearchResult` — `NoteSummary` + `score: float` + `snippet: str`.

### ID scheme — **ULID in frontmatter** (resolved)

A ULID stored in `id` is the canonical identity. ULIDs are stable across renames
and title edits, are lexicographically sortable by creation time, and avoid the
collision and reflow problems of content hashes (a hash changes every edit) and
of filename-as-identity (a filename changes when the title changes). The filename
is a separate, human-friendly `YYYY-MM-DD-<slug>.md` for browsability; if a slug
would collide, a short suffix is appended. Lookups resolve by `id`, not filename.

---

## 4. API surface

### REST — `/api/v1`

All endpoints require `Authorization: Bearer <token>`. Bodies are JSON unless noted.

| Method & path                 | Purpose | Request | Response |
|-------------------------------|---------|---------|----------|
| `POST /notes`                 | Create a note (idempotent). | `NoteCreate` | `201 Note` (or `200 Note` if `idempotency_key` already seen) |
| `GET /notes`                  | List notes, newest first. | query: `limit`, `cursor`, `tag` | `200 {items: NoteSummary[], next_cursor?}` |
| `GET /notes/{id}`             | Read a note in full. | — | `200 Note` / `404` |
| `DELETE /notes/{id}`          | Soft-delete (move to `.trash/`). | — | `204` / `404` |
| `POST /notes/{id}/restore`    | Restore from `.trash/`. | — | `200 Note` / `404` |
| `GET /search`                 | Full-text search. | query: `q` (required), `limit`, `tag` | `200 {items: SearchResult[]}` |
| `GET /trash`                  | List trashed notes. | query: `limit`, `cursor` | `200 {items: NoteSummary[], next_cursor?}` |
| `GET /healthz`                | Liveness/readiness (no auth). | — | `200 {status, version}` |

Errors use a consistent shape: `{ "error": { "code": string, "message": string } }`.
Pagination is opaque-cursor based. The OpenAPI schema generated from these routes
is the contract of record (`packages/contract`).

### MCP tools — `/mcp`

Exposed via `mcp.server.fastmcp`. Tool descriptions are written for LLM
consumption: concise, action-oriented, with an example. The five tools map onto
the same service layer as REST.

- **`save_note`** — "Save a new note to the vault. Use this to remember
  something for later: a fact, a snippet, a link, a decision. Provide a short
  `title` and the `body` as Markdown; add `tags` to make it findable. Returns the
  note's `id`. Example: `save_note(title='Postgres backup cmd', body='`pg_dump …`',
  tags=['ops','postgres'])`."
- **`search_notes`** — "Search the vault by keyword and return the best matches
  with a snippet and id. Use this before answering from memory, to ground your
  answer in what the user actually saved. Example: `search_notes(query='postgres
  backup')`."
- **`read_note`** — "Read one note in full by its `id` (get the id from
  `search_notes` or `list_notes`). Returns the title, tags, and full Markdown
  body. Example: `read_note(id='01J…')`."
- **`list_notes`** — "List recent notes (newest first) as id + title + tags,
  optionally filtered by `tag`. Use this to browse what exists when you don't
  have a search term. Example: `list_notes(tag='ops', limit=20)`."
- **`delete_note`** — "Move a note to the trash by `id` (soft-delete; it can be
  restored for 30 days). Confirm with the user before deleting. Example:
  `delete_note(id='01J…')`."

---

## 5. Storage layer

**Resolved: filesystem is the source of truth + a rebuildable SQLite FTS5 index.**

- **Why files are canonical.** Markdown on disk keeps the vault portable,
  inspectable, diffable, and durable independent of Bartleby. A user can read
  their notes with any text editor and back them up with any tool.
- **Why an index at all.** Walking and parsing the whole vault on every query is
  fine at tens of notes and painful at thousands. FTS5 gives ranked, prefix-aware
  full-text search. It ships inside the Python stdlib `sqlite3` (`ENABLE_FTS5` is
  on in CPython's bundled SQLite), so it adds **zero runtime dependencies** and no
  external service — appropriate for a single-user VPS.
- **Index is disposable.** The DB (default `<vault>/.bartleby/index.db`, gitignored
  and excluded from the vault listing) is a cache. Deleting it and reindexing
  reproduces it exactly from the files.

**Sync strategy:**

1. **Write-through.** The service layer updates the index inside the same
   operation that writes/moves a file (create, update, delete, restore). The file
   write is the commit point; the index update follows.
2. **Startup reconciliation.** On boot, compare each file's `mtime`/size against
   the index and re-index anything stale or missing, and drop index rows whose
   file is gone. This heals edits made to the vault while the server was down
   (e.g. a `git pull` or manual edit).
3. **Manual reindex.** A `bartleby reindex` CLI path (and an internal service
   call) rebuilds from scratch for recovery.

The storage layer lives in `packages/core` behind a `VaultStore` interface so the
index is an implementation detail the service layer owns, not something REST/MCP
see.

### Git-backing of the vault — **out of scope for v1** (resolved)

Bartleby will not manage git inside the vault in v1. A user who wants version
history can `git init` their vault directory themselves; the startup
reconciliation above already absorbs out-of-band changes. First-class git
integration (auto-commit, history browsing) is a candidate for a later version
and would get its own ADR. Keeping it out keeps v1 focused on the core loop.

---

## 6. Build and test pipeline

- **CI matrix (`ci.yml`).** Python 3.12 + 3.13; Node 20. Jobs: `ruff` + `mypy`
  (Python), `eslint` + `tsc` (TS), `pytest` (core + server), `vitest`
  (extension + web-ui), build all apps, and a **contract-drift** job that
  regenerates the OpenAPI schema from FastAPI and the TS types via
  `openapi-typescript`, then fails if the committed files differ. A
  `require-linked-issue` job fails any PR whose body has no issue reference.
  *Until the corresponding `pyproject.toml` / `package.json` exist, each job
  detects their absence and no-ops, so the pipeline is green on the docs-only
  bootstrap and activates automatically as code lands.*
- **Codegen commit strategy.** Generated artifacts in `packages/contract`
  (OpenAPI JSON + `.d.ts`) are **committed**, so the extension and web-ui build
  without running Python. CI is the gate that keeps them in sync with the server.
- **Test layout.** Tests live beside their package: `packages/core/tests/`,
  `apps/server/tests/`, `apps/extension/tests/`, `apps/web-ui/tests/`.
- **Sample-vault fixture.** A small committed vault under
  `packages/core/tests/fixtures/sample-vault/` (a handful of notes with varied
  frontmatter + a `.trash/` entry) backs both unit tests and a quick local
  manual run.

---

## 7. Deployment

- **Dockerfile (`infra/Dockerfile`).** Multi-stage: (1) build the SvelteKit UI to
  static assets; (2) assemble the Python server and copy the UI bundle into it.
  One final image contains server + UI; it serves everything on one port.
- **Compose (`infra/docker-compose.yml`).** One service, the vault mounted as a
  named/host volume, env from `.env`, a healthcheck on `/healthz`. A commented
  Caddy block shows TLS termination; `infra/Caddyfile.example` and
  `infra/bartleby.service` cover reverse-proxy and bare-metal systemd options.
- **Env var contract** (documented in `infra/.env.example`):

  | Var | Default | Meaning |
  |-----|---------|---------|
  | `BARTLEBY_VAULT_PATH` | `/data/vault` | Vault root on disk. |
  | `BARTLEBY_AUTH_TOKEN` | *(required)* | Bearer token for REST + MCP. |
  | `BARTLEBY_HOST` | `0.0.0.0` | Bind host. |
  | `BARTLEBY_PORT` | `8080` | Bind port. |
  | `BARTLEBY_TRASH_RETENTION_DAYS` | `30` | Days before trashed notes are purged. |
  | `BARTLEBY_INDEX_PATH` | `<vault>/.bartleby/index.db` | SQLite FTS5 index location. |
  | `BARTLEBY_CORS_ORIGINS` | *(empty)* | Comma-separated origins for the extension/web-ui. |
  | `BARTLEBY_LOG_LEVEL` | `info` | Log verbosity. |

- **First-run experience.** With no `BARTLEBY_AUTH_TOKEN`, the server refuses to
  start and prints a one-line generation hint. On first start it creates the vault
  directory, `.trash/`, and the index if missing. `docker compose up` then opening
  `/` should show an empty vault and a working `/healthz`.

---

## 8. Phased delivery

Five independently shippable milestones. Each milestone is a roadmap item: when a
PR completes one, **tick its box in this file in the same PR** (see `CLAUDE.md`).

### Phase 0 — Bootstrap (this PR)
- [ ] Planning, governance, ADRs, CI/CD, infra config, docs site, workflow automation. *(No application code.)*

### Phase 1 — Core + storage
- [ ] `packages/core` Pydantic models (`Note`, `NoteCreate`, `NoteSummary`, `SearchResult`).
- [ ] `VaultStore`: read/write Markdown + YAML frontmatter; ULID + slug filename.
- [ ] Soft-delete to `.trash/`, restore, retention purge.
- [ ] SQLite FTS5 index: write-through, startup reconciliation, reindex.
- [ ] Idempotency by `idempotency_key`.
- [ ] Unit tests + sample-vault fixture.

### Phase 2 — Server (MCP first, then REST)
- [ ] FastAPI app skeleton + bearer auth + `/healthz`.
- [ ] MCP endpoint with the five tools (`save_note`, `search_notes`, `read_note`, `list_notes`, `delete_note`).
- [ ] REST `/api/v1` endpoints per §4.
- [ ] OpenAPI export + committed TS types in `packages/contract`; CI drift gate live.
- [ ] Static-file mounting for the UI bundle.

### Phase 3 — Extension
- [ ] MV3 extension: Readability + Turndown clip of the active tab.
- [ ] Options page (server URL + bearer token), `activeTab` + configurable host permission.
- [ ] `POST /api/v1/notes` with `source_url` + `idempotency_key`.
- [ ] Chrome + Firefox build producing store-ready `.zip` artifacts.

### Phase 4 — Web UI
- [ ] SvelteKit static app: vault browser, read-only Markdown viewer, delete-with-confirm.
- [ ] Consumes committed contract types; bundle served at `/`.

### Phase 5 — Polish + release
- [ ] Docker image to GHCR via `release.yml`; extension artifacts attached to the Release.
- [ ] Docs site filled out (install, configuration, MCP + API reference).
- [ ] First tagged release `v0.1.0`; CHANGELOG cut.

---

## 9. Open risks and mitigations

| Risk | Mitigation |
|------|------------|
| **MCP SDK / spec churn.** The MCP Python SDK and spec are evolving. | Pin the SDK version; keep MCP tool handlers thin over `packages/core`; cover them with tests against MCP Inspector. |
| **Index/file divergence** after out-of-band edits. | Index is disposable; startup reconciliation + `reindex` rebuild it from files (the source of truth). |
| **Concurrent writes** to the same note. | Single-user assumption; serialize writes in `VaultStore` and use `updated_at` for last-writer-wins. Revisit only if multi-writer becomes real. |
| **Bearer token leakage** (single shared secret). | Document HTTPS-only deployment (Caddy example); token in env, never logged; server makes no outbound calls. Tighter auth (OAuth) deferred — would get an ADR. |
| **Extension store review friction** (permissions). | Minimal permissions (`activeTab` + user-configured host); justify each in the listing; source-mapped Firefox builds; reproducible CI artifacts. |
| **FTS5 unavailable** in some exotic Python build. | CPython ships FTS5; document the requirement and fail fast at startup with a clear message if the module is missing. |
| **Filename slug collisions.** | Resolve by appending a short suffix; identity is the ULID, not the filename, so collisions are cosmetic. |
