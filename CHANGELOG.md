# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Extension icons (16/32/48/128) using the Bartleby quill brand mark, shown in
  the browser toolbar and the Chrome Web Store / Firefox AMO listings.

### Changed
- Web UI and documentation-site favicons now use the Bartleby quill brand mark
  (replacing the placeholder `B` mark).

## [0.1.0] - 2026-05-24

### Added
- Project bootstrap: implementation plan, governance docs (README, security
  policy, contributing guide), ADRs, CI/CD workflows, deployment scaffolding,
  MkDocs documentation site, and the issue-first workflow automation.
- `packages/core` (`bartleby_core`): the vault core library — Pydantic models,
  Markdown + YAML frontmatter storage (`VaultStore`), a rebuildable SQLite FTS5
  search index, soft-delete/restore/retention-purge, idempotent create, startup
  reconciliation, full reindex, and the `python -m bartleby_core.reindex` entry
  point.
- `apps/server` (`bartleby_server`): the FastAPI server — REST `/api/v1` (notes,
  search, trash), the MCP endpoint `/mcp` with five tools, `/healthz`, shared
  bearer-token auth, and a conditional static UI mount; the `bartleby` and
  `bartleby-export-openapi` commands.
- `packages/contract`: the committed OpenAPI schema and generated TypeScript
  types, plus the pnpm workspace; CI now enforces contract drift.
- `apps/extension`: a Manifest V3 browser extension for Chrome and Firefox, built
  with WXT. One click clips the active tab to Markdown (Readability + Turndown in
  an on-demand content script) and POSTs it to `/api/v1/notes` with `source_url`
  and an idempotency key. Options page stores the server URL + bearer token and
  requests the server-origin host permission at runtime; minimal permissions
  (`activeTab`, `storage`, `scripting`). No outbound calls except to the
  configured server.
- `apps/web-ui`: a SvelteKit static SPA (Svelte 5, Tailwind v4) served by the
  server at `/` — connect with a bearer token, browse notes (paginated), read a
  note's Markdown (sanitized with DOMPurify), delete with confirm, full-text
  search, and view/restore trashed notes. Single route with query-string state.

[Unreleased]: https://github.com/t11z/bartleby/compare/v0.1.0...main
[0.1.0]: https://github.com/t11z/bartleby/releases/tag/v0.1.0
