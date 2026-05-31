# Store submission

Everything needed to publish the Engram extension to the **Chrome Web Store**
and **Firefox Add-ons (AMO)**. The build artifacts themselves are produced by
`release.yml` on every `v*.*.*` tag (attached to the GitHub Release) and can be
published automatically via the gated `publish-extension` job — see
[Automated publishing](#automated-publishing).

## Files here

- [`listing.md`](./listing.md) — listing copy (name, summary, description,
  category, single-purpose statement) for both stores.
- [`permissions.md`](./permissions.md) — per-permission justifications to paste
  into the review forms.
- Privacy policy — published at <https://t11z.github.io/engram/privacy/>
  (source: [`docs-site/docs/privacy.md`](../../../docs-site/docs/privacy.md)).
  Both stores require a public privacy-policy URL.

## One-time setup

You need a developer account per store (these are the maintainer's manual
steps — they can't be automated):

- **Chrome Web Store** — register at
  <https://chrome.google.com/webstore/devconsole> (one-time US$5 fee).
- **Firefox AMO** — create an account at <https://addons.mozilla.org>
  (no fee).

Both listings also need **screenshots** (Chrome: 1280×800 or 640×400; AMO:
similar). Capture the options page and a clip in action; store them alongside
this file if you want them version-controlled.

## Manual submission checklist

1. Bump `version` in `apps/extension/package.json` and add a `CHANGELOG.md`
   entry. (WXT derives the manifest version from `package.json`.)
2. Build store-ready zips from a clean tree:
   ```bash
   pnpm --filter extension zip            # Chrome zip
   pnpm --filter extension zip -b firefox # Firefox zip + sources zip
   ```
   Zips land in `apps/extension/dist/`.
3. **Chrome**: upload the `*-chrome.zip`, fill in the listing from
   `listing.md`, paste permission justifications from `permissions.md`, set the
   privacy-policy URL, complete the data-use disclosures (none collected by the
   authors), submit.
4. **Firefox**: upload the `*-firefox.zip`, attach the `*-sources.zip` (AMO
   requires source for built add-ons; our builds also ship source maps), fill
   in the listing, set the privacy-policy URL, submit.
5. Verify the public extension once approved: install, configure a test server,
   clip a page, confirm the note lands in the vault.

## Automated publishing

`release.yml` includes a `publish-extension` job that runs
[`wxt submit`](https://wxt.dev/guide/essentials/publishing.html) for both
stores. It is **opt-in**: it only runs when the repository variable
`PUBLISH_EXTENSION` is set to `true`, so tagging a release never publishes
unexpectedly.

Configure these repository **secrets** (Settings → Secrets and variables →
Actions) before enabling it:

| Secret | Store | Where to get it |
| --- | --- | --- |
| `CHROME_EXTENSION_ID` | Chrome | The item ID from the Web Store dashboard. |
| `CHROME_CLIENT_ID` | Chrome | Google Cloud OAuth client (Chrome Web Store API). |
| `CHROME_CLIENT_SECRET` | Chrome | Same OAuth client. |
| `CHROME_REFRESH_TOKEN` | Chrome | Generated once via the OAuth flow. |
| `FIREFOX_EXTENSION_ID` | Firefox | `engram@t11z.github.io` (the gecko id). |
| `FIREFOX_JWT_ISSUER` | Firefox | AMO API credentials (`user:...`). |
| `FIREFOX_JWT_SECRET` | Firefox | AMO API secret. |

`wxt submit init` can walk you through obtaining the Chrome OAuth credentials
and AMO API keys. The **first** Chrome submission must be done manually in the
dashboard; the API can only publish updates to an existing item.

Then set `PUBLISH_EXTENSION=true` and push a `v*.*.*` tag.
