# 0005. Server-side URL fetch for capture-by-link

- Status: accepted
- Date: 2026-05-27

## Context and problem statement

The browser extension is the only existing way to ingest a web page into the
vault. It runs Readability + Turndown in the user's tab, then POSTs Markdown to
`POST /api/v1/notes`. There is no iOS app and no equivalent share-sheet path on
mobile.

We want an iPhone user to share any URL from Safari into Engram with a single
tap. Building a native iOS app for this is disproportionate — it needs Xcode, a
developer account, and ongoing maintenance for one HTTP POST. An Apple Shortcut
costs none of that, but a Shortcut cannot run Readability: at best it forwards
the URL.

The implication is that *something* has to fetch the page and turn it into
Markdown. Either:

- every client owns extraction (today's pattern, repeated per platform), or
- the server owns extraction and clients become URL-forwarders.

`CLAUDE.md` documents Engram's "no outbound calls" stance: no telemetry, no
update pings, the browser extension talks only to the user's own server. A new
server endpoint that fetches the URL the user just supplied technically breaks
that — it makes an outbound HTTP call. The question is whether that is the same
class of thing.

## Considered options

- **Server-side fetch and extract.** Add `POST /api/v1/links { url }`. The
  server fetches, runs an extractor, and creates the note via the existing
  `NoteService.create` path. Every future client (iOS Shortcut, Android, CLI,
  third-party) sends only the URL.
- **Client-side extraction in every client.** Mirror the browser-extension
  pattern: each new client embeds Readability or an equivalent. For iOS that
  means a native Share Extension with Swift + an HTML parser library.
- **Hybrid bookmarklet.** A JavaScript bookmark that runs Readability in
  Safari and POSTs Markdown to `/api/v1/notes`. Works on iOS but does not show
  up in the share sheet, so the user has to actively pick the bookmark.

## Decision

Add `POST /api/v1/links`. The server fetches the URL, extracts the article to
Markdown, and creates the note via the existing service. The Apple Shortcut and
any future thin client only sends `{ "url": "..." }` with the bearer token.

The outbound fetch is gated by:

- A scheme allowlist (`http`, `https`); URLs with embedded user-info are
  refused.
- An SSRF guard that resolves the host with `socket.getaddrinfo` and refuses
  any address in private, loopback, link-local, multicast, reserved, or
  unspecified ranges. The guard re-runs on every redirect (manual follow,
  cap 5 hops).
- A size cap (5 MB), a timeout (10 s), and a Content-Type allowlist
  (`text/html`, `application/xhtml+xml`).

Extraction uses `trafilatura` as the primary path (outputs Markdown directly)
with `markdownify` as the fallback for pages trafilatura returns empty on.

## Rationale

The cost of "no outbound calls" was always that we trade convenience for
auditability. The decisive question here is whether the user can predict every
outbound call the server makes. They can: this endpoint fetches *only* the URL
the user just sent in the same request, with no background, no caching, no
discovery. It is operationally identical to the user pasting that URL into a
browser. Conversely, asking every future client to embed Readability would
multiply the maintenance surface and produce divergent extraction quality
across platforms.

The hybrid bookmarklet was rejected because it cannot appear in the iOS share
sheet (Safari only ever shows registered apps and Shortcuts there), and so
fails the one-tap goal that motivated the work.

## Consequences

- The README's privacy stance must be updated: "no outbound calls except the
  ones you initiate by sharing a URL." Telemetry is still none.
- All future clients (iOS Shortcut, future Android app, CLI `engram clip
  <url>`, third-party integrations) get this feature for free without code
  changes here.
- The server now depends on `httpx`, `trafilatura`, `markdownify`, and
  `beautifulsoup4`. `trafilatura` performs a one-time model load on first use
  (~10 MB on disk) which is acceptable for a long-running server.
- If we ever proxy *arbitrary* fetches (not bound to a single note creation),
  the SSRF posture has to be re-audited and probably tightened (deny lists for
  internal corporate ranges via configuration).
- Pages that demand JavaScript to render or that paywall the article body will
  produce stub notes. The endpoint does not try to bypass this; the user can
  see the stub in their vault and re-share or edit by hand.
