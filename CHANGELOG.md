# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- A static, interactive demo of the web UI published on GitHub Pages at
  <https://t11z.github.io/engram/demo/>. Built with `VITE_ENGRAM_DEMO=1`, the UI
  runs against an in-memory mock store seeded with curated sample notes instead
  of a live `/api/v1` server, so newcomers can browse, search, and try
  delete/restore entirely in the browser (state resets on reload). The demo is
  built and deployed alongside the docs site by `pages.yml`. The README links to
  it in place of the former static screenshot.

## [0.3.0] - 2026-05-31

### Added
- Browser-extension store-submission kit under `apps/extension/store/` (listing
  copy, per-permission justifications, and a submission checklist) plus a public
  privacy policy at `docs-site/docs/privacy.md`
  (<https://t11z.github.io/engram/privacy/>), both required by the Chrome Web
  Store and Firefox AMO. Release publishing is now automated by an opt-in
  `publish-extension` job in `release.yml` that runs `wxt submit` for both
  stores, gated on the `PUBLISH_EXTENSION` repository variable.
- Extension icons (16/32/48/128) using the Engram quill brand mark, shown in
  the browser toolbar and the Chrome Web Store / Firefox AMO listings.

### Changed
- Rolled the Engram design language (warm dark ink, amber accent, Quicksand /
  IBM Plex type) onto the surfaces that still used the old look: the browser
  extension's options page and the server's OAuth authorize page are now dark and
  branded, and the brand mark appears in the documentation-site header and on the
  landing-page hero. The extension toolbar icons and the web-UI / docs-site
  favicons are regenerated from the amber logomark on a rounded ink "stamp"
  (see `infra/render-brand-assets.py`), replacing the old quill-on-cream mark.
- **Renamed the project from Bartleby to Engram.** This is a breaking change with
  no backward-compatibility shims: configuration env vars are now `ENGRAM_*`
  (previously `BARTLEBY_*`), the CLI command is `engram` (previously `bartleby`),
  the Python packages/modules are `engram-core`/`engram-server` (modules
  `engram_core`/`engram_server`), and the vault's index/OAuth directory moved from
  `<vault>/.bartleby/` to `<vault>/.engram/`. Existing deployments must update
  their `.env`, rename the systemd unit to `engram.service`, and rename the
  `.bartleby/` directory in each vault to `.engram/`. The Docker image is now
  `ghcr.io/t11z/engram`.
- Web UI and documentation-site favicons now use the Engram quill brand mark
  (replacing the placeholder `B` mark).

### Fixed
- Added stable keys to the Web UI's tag `{#each}` blocks, fixing Svelte
  list-reconciliation warnings.

### Security
- Force the transitive `tmp` npm dependency (pulled in via `wxt` → `web-ext-run`)
  to `^0.2.7` through a `pnpm.overrides` entry, picking up the upstream
  sanitization of `prefix`/`postfix`/`dir` options that closes CVE-2026-44705
  (path traversal out of the temp directory). Dependabot alert #3.

## [0.2.1] - 2026-05-27

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
- Extension: a right-click "Open Engram server" entry on the toolbar icon's
  context menu that opens the configured server's web UI in a new tab (or the
  options page when no server is configured yet).

### Fixed
- MCP transport is now reachable at the bare `/mcp` path, not only `/mcp/`. The
  OAuth protected-resource metadata advertises `<public_url>/mcp` (no trailing
  slash) and claude.ai connects to exactly that, but the mounted transport only
  answered `/mcp/`, so a bare `/mcp` request fell through to the static-UI mount
  (404 for `GET`, 405 for `POST`) and the connector failed right after
  authorizing. The server now serves the advertised URL directly.

## [0.2.0] - 2026-05-24

### Added
- Optional embedded OAuth 2.1 authorization server so the MCP endpoint can be
  added to claude.ai (Web) as a Custom Connector. Opt in by setting
  `ENGRAM_PUBLIC_URL` (the public HTTPS origin / token issuer) and
  `ENGRAM_OAUTH_PASSWORD` (gates the login/consent page). Supports Dynamic
  Client Registration, the authorization-code + PKCE flow, refresh-token
  rotation, and revocation, with clients and tokens persisted in
  `<vault>/.engram/oauth.db`. The static `ENGRAM_AUTH_TOKEN` keeps working —
  `/mcp` accepts either an OAuth token or the static token — and when
  `ENGRAM_PUBLIC_URL` is unset the server behaves exactly as before.

## [0.1.1] - 2026-05-24

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
- `packages/core` (`engram_core`): the vault core library — Pydantic models,
  Markdown + YAML frontmatter storage (`VaultStore`), a rebuildable SQLite FTS5
  search index, soft-delete/restore/retention-purge, idempotent create, startup
  reconciliation, full reindex, and the `python -m engram_core.reindex` entry
  point.
- `apps/server` (`engram_server`): the FastAPI server — REST `/api/v1` (notes,
  search, trash), the MCP endpoint `/mcp` with five tools, `/healthz`, shared
  bearer-token auth, and a conditional static UI mount; the `engram` and
  `engram-export-openapi` commands.
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

[Unreleased]: https://github.com/t11z/engram/compare/v0.3.0...main
[0.3.0]: https://github.com/t11z/engram/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/t11z/engram/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/t11z/engram/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/t11z/engram/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/t11z/engram/releases/tag/v0.1.0
