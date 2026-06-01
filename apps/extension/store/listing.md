# Listing copy

Reusable text for the Chrome Web Store and Firefox AMO listings. Keep this in
sync with the manifest (`apps/extension/wxt.config.ts`).

## Name

```
Engram
```

## Summary / short description

> Chrome limit: 132 chars. AMO summary: 250 chars.

```
Clip the page you're reading to clean Markdown and save it to your own
self-hosted Engram server. No accounts, no tracking.
```

## Category

- **Chrome**: Productivity
- **Firefox**: Bookmarks / Productivity

## Single-purpose description (Chrome requires this)

```
Engram has one purpose: when you click its toolbar icon, it extracts the
readable article from the current tab, converts it to Markdown, and saves it as
a note to the Engram server you configure. It does nothing else.
```

## Full description

```
Engram is a web clipper for your own notes — not a cloud service.

Point it at a Engram server you host yourself, then clip any article with one
click. Engram extracts the readable content, converts it to clean Markdown
(headings, lists, links, code intact), and saves it as a note with the source
URL, so your reading turns into a searchable Markdown vault you own.

What makes it different:

• Self-hosted. There is no Engram cloud and no default server. You enter your
  own server URL and token on the options page; nothing works until you do.
• Private by design. No analytics, no telemetry, no phone-home. The only network
  request goes to your server. The extension's authors operate no servers and
  receive no data.
• Minimal permissions. Engram reads a page only when you click it (activeTab),
  and asks for access to just your server's address — never to all the sites you
  visit by default.
• Clean Markdown. Powered by Readability and Turndown, the same extraction stack
  trusted for reader views, all bundled locally — no remote code.

You need a running Engram server (https://github.com/t11z/engram) to use
this extension.
```

## URLs

- **Homepage / support**: <https://github.com/t11z/engram>
- **Privacy policy**: <https://t11z.github.io/engram/privacy/>
- **Documentation**: <https://t11z.github.io/engram/>

## Data collection disclosure

```
required: websiteContent

When the user clicks the toolbar icon, the extension reads the current page's
content and transmits it to the user's own self-hosted Engram server to save it
as a note. This is the extension's sole purpose. The page content goes only to
the server URL the user configures; the extension's authors operate no servers
and receive no data. No telemetry, analytics, or technical/interaction data is
collected.
```

## Notes for reviewers

```
This extension requires a self-hosted backend. To test end-to-end you must run a
Engram server and enter its URL + bearer token on the options page. Setup:
https://t11z.github.io/engram/quick-start/

Without a configured server the extension intentionally does nothing. The broad
optional host permission exists only so the user can grant access to their own
server's origin at runtime (the server address is not known at build time); it
is requested for that single origin from the options page, never for all sites.
```
