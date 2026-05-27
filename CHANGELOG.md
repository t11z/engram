# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Security
- Force the transitive `tmp` npm dependency (pulled in via `wxt` → `web-ext-run`)
  to `^0.2.7` through a `pnpm.overrides` entry, picking up the upstream
  sanitization of `prefix`/`postfix`/`dir` options that closes CVE-2026-44705
  (path traversal out of the temp directory). Dependabot alert #3.

### Fixed
- MCP transport is now reachable at the bare `/mcp` path, not only `/mcp/`. The
  OAuth protected-resource metadata advertises `<public_url>/mcp` (no trailing
  slash) and claude.ai connects to exactly that, but the mounted transport only
  answered `/mcp/`, so a bare `/mcp` request fell through to the static-UI mount
  (404 for `GET`, 405 for `POST`) and the connector failed right after
  authorizing. The server now serves the advertised URL directly.

### Added
- iOS share-sheet support via a new `POST /api/v1/links` endpoint. The server
  fetches the supplied URL, extracts the article body to Markdown, and creates
  a note through the existing write path — clients only have to send
  `{ "url": "..." }` plus the bearer token. An Apple Shortcut recipe in
  [`docs/ios-shortcut.md`](./docs/ios-shortcut.md) wires this into Safari's
  share sheet without an App-Store app. The endpoint applies an SSRF guard
  (rejecting loopback/private/link-local hosts, re-checked on every redirect),
  a 5 MB size cap, a 10 s timeout, and an HTML-only Content-Type allowlist;
  see [ADR-0005](./docs/adr/0005-server-side-url-fetch.md).
- Optional embedded OAuth 2.1 authorization server so the MCP endpoint can be
  added to claude.ai (Web) as a Custom Connector. Opt in by setting
  `BARTLEBY_PUBLIC_URL` (the public HTTPS origin / token issuer) and
  `BARTLEBY_OAUTH_PASSWORD` (gates the login/consent page). Supports Dynamic
  Client Registration, the authorization-code + PKCE flow, refresh-token
  rotation, and revocation, with clients and tokens persisted in
  `<vault>/.bartleby/oauth.db`. The static `BARTLEBY_AUTH_TOKEN` keeps working —
  `/mcp` accepts either an OAuth token or the static token — and when
  `BARTLEBY_PUBLIC_URL` is unset the server behaves exactly as before.
- Extension icons (16/32/48/128) using the Bartleby quill brand mark, shown in
  the browser toolbar and the Chrome Web Store / Firefox AMO listings.
- Extension: a right-click "Open Bartleby server" entry on the toolbar icon's
  context menu that opens the configured server's web UI in a new tab (or the
  options page when no server is configured yet).

### Changed
- Web UI and documentation-site favicons now use the Bartleby quill brand mark
  (replacing the placeholder `B` mark).

### Security
- Resolve two Dependabot alerts in transitive npm dependencies via
  `pnpm.overrides`: `cookie` (`<0.7.0` → `^0.7.0`, GHSA-pxg6-pf52-xh8x, via
  `@sveltejs/kit`) and `uuid` (`<11.1.1` → `^11.1.1`, GHSA-w5hq-g745-h8pq, via
  `wxt > web-ext-run > node-notifier`).

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
