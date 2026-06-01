# Permission justifications

Paste these into the store review forms. They must match the manifest in
`apps/extension/wxt.config.ts`. Keep both in sync — adding any permission
requires updating this file and the PR description (see
[`apps/extension/CLAUDE.md`](../CLAUDE.md)).

Declared in the manifest:

- `permissions: ["activeTab", "storage", "scripting", "contextMenus"]`
- `optional_host_permissions: ["*://*/*"]`
- `browser_specific_settings.gecko.data_collection_permissions: { required: ["websiteContent"] }`

## Data collection (Firefox AMO)

```
required: ["websiteContent"]
```

Firefox requires every new extension to declare its data collection. Engram's
single purpose is to transmit the content of the page you clip to your server,
so we declare websiteContent as a required collection. Mozilla defines "data"
broadly — all data the extension transmits, including its core functionality and
regardless of destination — so this is declared even though the data goes only
to the user's own self-hosted server and never to the extension's authors or any
third party. No telemetry, analytics, or technical/interaction data is collected,
so there is no optional set.

## activeTab

```
Used to read the content of the current tab only when the user clicks the
extension's toolbar icon, so it can be clipped to Markdown. The extension never
reads tabs in the background or without an explicit user action.
```

## scripting

```
Used to inject a single extractor script into the active tab on user action
(chrome.scripting.executeScript), which reads the article and returns it for
Markdown conversion. Injection happens only for the tab the user clicked,
under the access granted by activeTab.
```

## storage

```
Used to persist the user's two settings on their device: the URL of their
self-hosted Engram server and the bearer token used to authenticate to it.
No other data is stored and nothing is synced to third parties.
```

## contextMenus

```
Adds a single "Open Engram server" entry to the toolbar icon's right-click
menu, which opens the user's configured server in a new tab. No host permission
is needed for this.
```

## Optional host permission (`*://*/*`)

```
This is an OPTIONAL host permission and is NOT granted by default. The extension
saves notes by POSTing to the user's own Engram server, whose origin is not
known at build time (users self-host on arbitrary domains, LAN addresses, or
ports, over http or https). When the user enters their server URL on the options
page, the extension requests host access for ONLY that single origin via
chrome.permissions.request(). The broad pattern is the requestable set, not a
default grant; the extension never accesses arbitrary sites.
```
