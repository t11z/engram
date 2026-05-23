# CLAUDE.md — extension

Working manual for `apps/extension` (Manifest V3, Chrome + Firefox). One job:
clip the active tab to Markdown and POST it to the user's server. Architecture is
in [`/docs/IMPLEMENTATION_PLAN.md`](../../docs/IMPLEMENTATION_PLAN.md).

> Single purpose. No management UI inside the extension, no default server URL,
> no analytics, no phone-home. The only network call is to the user-configured
> server.

## Manifest V3 constraints

- Background logic runs in a **service worker** — no persistent background page,
  no long-lived global state. Assume it can be torn down between events.
- No remote code. Everything ships in the package; bundle dependencies
  (Readability, Turndown) locally.
- Clipping reads the page via `activeTab` (granted on user action), converts with
  Readability → Turndown, then POSTs to `/api/v1/notes` with `source_url` and an
  `idempotency_key`.

## Permission policy

Minimum surface, and **justify any expansion in the PR and the store listing**:

- `activeTab` — read the current page only when the user invokes the clip action.
- `storage` — persist the server URL and bearer token from the options page.
- A **configurable host permission** for the user's server origin — not `<all_urls>`.

Adding any permission requires a one-line justification in the PR description.

## Build: Chrome + Firefox artifacts

The build pipeline emits a store-ready `.zip` per target:

```bash
pnpm --filter extension build          # both targets -> apps/extension/dist/
pnpm --filter extension build:chrome
pnpm --filter extension build:firefox
```

Builds are reproducible; Firefox builds ship source maps for AMO review. CI
produces the same artifacts on release tags.

## Load unpacked for local testing

- **Chrome**: `chrome://extensions` → enable Developer mode → *Load unpacked* →
  select the Chrome build dir.
- **Firefox**: `about:debugging` → This Firefox → *Load Temporary Add-on* →
  pick `manifest.json` in the Firefox build dir.

Set the server URL + token in the options page, open any article, and clip it;
confirm a note appears in the vault.

## Options page / config persistence

The options page writes `{ serverUrl, token }` to extension `storage`. The
service worker reads from `storage` on each clip (don't cache across worker
restarts). There is no default server URL — an unconfigured extension does
nothing until the user sets one.

## Before submitting a store update

- Bump the version in `manifest.json` and note it in `CHANGELOG.md`.
- Re-check the permission list is still minimal; update listing justifications.
- Rebuild both targets from a clean tree; test load-unpacked on both browsers.
- Confirm no outbound call goes anywhere except the configured server.
