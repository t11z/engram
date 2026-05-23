# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/t11z/bartleby/commits/main
