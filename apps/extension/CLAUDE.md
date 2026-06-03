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

## Extraction & the substantive-content guard

Extraction logic lives in `src/lib/extract.ts` (a pure `Document → ExtractResponse`
module, so it is unit-testable under jsdom without the WXT wrapper); the
`extractor.content.ts` content script is just the messaging adapter. The pipeline
tries Readability first, falls back to a de-chromed copy of the body, and only then
gives up. Each candidate must pass `isSubstantive()` — a generic heuristic that
rejects only the empty, the link/nav-dominated, and small fragments of a much
larger body (a low **coverage** of the page's de-chromed content). It deliberately
does **not** reject content for being short: a definition, quote, or short note is
valid, so short content passes when it covers the page. When nothing qualifies the
extension **fails honestly with an error badge instead of silently saving a
link-only stub note**. Keep the heuristic generic; no per-site logic here.

Tests run real Readability against a labeled HTML-fixture corpus in
`test/fixtures/`, asserting outcome class (substantive vs. correctly-rejected), not
exact Markdown. **When a page is reported as mis-clipped, trim it into a new fixture,
label its expected outcome, then tune `extract.ts` until it passes without breaking
the others** — the corpus is the regression net.

## Permission policy

Minimum surface, and **justify any expansion in the PR and the store listing**:

- `activeTab` — read the current page only when the user invokes the clip action.
- `scripting` — inject the one-off extractor into the active tab on user action
  (`chrome.scripting.executeScript`); scoped to the tab `activeTab` just granted.
- `storage` — persist the server URL and bearer token from the options page.
- `contextMenus` — add a right-click entry on the toolbar icon to open the
  configured server's web UI (no host permission needed; it opens a normal tab).
- A **configurable host permission** for the user's server origin — not `<all_urls>`.
  Declared as `optional_host_permissions` and requested at runtime from the
  options page for **only** the origin the user enters (`options/main.ts`). The
  broad pattern is the requestable set (the self-hosted origin is unknown at
  build time), never a default grant.

Adding any permission requires a one-line justification in the PR description and
an update to [`store/permissions.md`](./store/permissions.md).

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

## Store submission

Listing copy, permission justifications, and the submission checklist live in
[`store/`](./store/). The privacy policy required by both stores is published at
<https://t11z.github.io/engram/privacy/> (source:
`docs-site/docs/privacy.md`). Publishing is automated by the opt-in
`publish-extension` job in `.github/workflows/release.yml` (`wxt submit`, gated
on the `PUBLISH_EXTENSION` repo variable); see
[`store/README.md`](./store/README.md) for the required secrets.

## Before submitting a store update

- The published version is the release tag (`v1.2.3` → `1.2.3`): `release.yml`
  sets `ENGRAM_EXTENSION_VERSION` from the tag so the manifest matches the GitHub
  Release. No manual `package.json` bump is needed to ship; the committed
  `version` is only the local-dev fallback when that env var is unset.
- Re-check the permission list is still minimal; update
  [`store/permissions.md`](./store/permissions.md) and the listing.
- Rebuild both targets from a clean tree; test load-unpacked on both browsers.
- Confirm no outbound call goes anywhere except the configured server.
