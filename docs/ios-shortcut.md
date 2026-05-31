# iOS share sheet → Engram

Share any web page from Safari (or any iOS browser) into your vault with a
single tap, using an **Apple Shortcut** that calls the server's `POST
/api/v1/links` endpoint. Engram fetches the URL, extracts the article to
Markdown, and saves it as a note.

This works because:

- The endpoint accepts just `{ "url": "..." }` — the Shortcut stays simple.
- The server runs the same article extractor for every client, so a one-shot
  Shortcut produces the same quality of note as the browser extension.
- Authentication is the same static `ENGRAM_AUTH_TOKEN` used by the
  extension; no OAuth flow needed for a personal Shortcut.

There is no App Store app to install and no Xcode required.

## Prerequisites

- A reachable Engram server. The Shortcut runs on your iPhone, so the URL
  you point it at must resolve and connect *from the phone* — not just from
  your laptop. Same model as the browser extension. Common setups:
  - **Tailscale / WireGuard**: the phone joins your private network; point the
    Shortcut at the magic-DNS name (`http://engram.tailnet-name.ts.net`).
  - **Public HTTPS**: a reverse proxy (Caddy, Cloudflare Tunnel, etc.) in
    front of the server; point the Shortcut at the public URL.
  - **Same Wi-Fi only**: works as a proof-of-concept on `http://<lan-ip>:8080`
    when you are home, but the share sheet is most useful when out.
- The `ENGRAM_AUTH_TOKEN` value the server was started with.

## Build the Shortcut by hand

This is the recommended path — the recipe is short and survives iOS updates.
On the iPhone, open the **Shortcuts** app and tap **+** to add a new shortcut.

1. **Configure share-sheet input.** Tap the settings icon ("i" → "Details"),
   enable **Use with Share Sheet**, set **Share Sheet Types** to **URLs** (and
   optionally **Safari web pages**). Disable the other types — they will not
   produce useful input.
2. **Text** action — paste your server's base URL:
   ```
   https://engram.example.com/api/v1/links
   ```
3. **Text** action — paste your bearer token:
   ```
   <your ENGRAM_AUTH_TOKEN>
   ```
4. **Dictionary** action with one key:
   - `url` → set value to **Shortcut Input** (variable picker → Shortcut Input).
5. **Get Contents of URL** action:
   - URL: the variable from step 2.
   - Method: **POST**.
   - Headers:
     - `Authorization` → `Bearer ` + the variable from step 3.
     - `Content-Type` → `application/json`.
   - Request Body: **JSON** → the Dictionary from step 4.
6. **Get Dictionary Value** → get value for key `error` from the previous
   action's output.
7. **If** the value has **any value**:
   - **Show Notification** → "Engram: " + (Dictionary value for key `error`
     → key `message`).
   - **Otherwise**:
     - **Get Dictionary Value** → get value for key `title` from the
       Get-Contents-of-URL output.
     - **Show Notification** → "Saved: " + that value.
8. Rename the Shortcut to **Save to Engram**. Optionally pick an icon and
   colour.

That is the whole flow. From Safari, tap the share button on any page, scroll
to **Save to Engram**, and the article lands in your vault. Open the web UI
at `/` to confirm.

## Smoke test from the desktop first

Before fighting the iPhone, confirm the endpoint works from your laptop with
`curl`:

```bash
curl -sX POST https://engram.example.com/api/v1/links \
  -H 'Authorization: Bearer <your-token>' \
  -H 'Content-Type: application/json' \
  -d '{"url": "https://en.wikipedia.org/wiki/Engram,_the_Scrivener"}' | jq
```

Expected: `201` and a JSON `Note` with `body` populated and `source_url` set
to the final URL after redirects. Repeating the same call returns `200` with
the same `id` — `/links` is idempotent by URL hash.

## Error shapes

The Shortcut already covers the success path. For reference, the endpoint
returns Engram's standard error envelope:

```json
{ "error": { "code": "blocked_host", "message": "..." } }
```

Codes you may hit:

| HTTP | code                       | when                                                     |
|-----:|----------------------------|----------------------------------------------------------|
|  400 | `blocked_host`             | URL targets a non-public address (loopback/private/etc). |
|  413 | `link_too_large`           | Response exceeded the 5 MB cap.                          |
|  415 | `unsupported_content_type` | Response was not HTML (e.g. a PDF).                      |
|  422 | `link_unreachable`         | Remote host returned 4xx/5xx or invalid redirect.        |
|  422 | `extraction_failed`        | Page fetched but nothing extractable.                    |
|  504 | `link_timeout`             | Fetch took longer than 10 s.                             |

## Notes

- The Shortcut uses the same static `ENGRAM_AUTH_TOKEN` as the browser
  extension. If you rotate the token on the server, edit the Text action in
  the Shortcut.
- Tag-picker UI in the Shortcut is intentionally not included — one tap is
  the point. The endpoint accepts an optional `tags` array if you want to
  fork the Shortcut and add a **Choose from List** action.
- Engram does not try to bypass paywalls or run JavaScript. Pages that need
  client-side rendering will save as a stub, which you can edit in the vault.
