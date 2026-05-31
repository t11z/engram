# Privacy policy

_Last updated: 2026-05-31_

Bartleby is self-hosted note-taking software. This policy covers the **Bartleby
browser extension** for Chrome and Firefox, which clips the page you are viewing
to Markdown and saves it to a Bartleby server **that you run and configure**.

## The short version

- The extension has **no default server**, no analytics, no telemetry, and makes
  **no "phone-home" calls**. It does nothing until you point it at your own
  server.
- The **only** network request the extension makes with your data goes to the
  server URL **you** enter on its options page.
- The extension's authors operate **no servers** and **receive no data** from it.

## What the extension processes

The extension only acts when you explicitly invoke it (clicking its toolbar icon
on the current tab). When you do, it processes, for that one page:

- the page's article content, converted to Markdown;
- the page title; and
- the page URL (stored as the note's `source_url`).

This data is sent in a single `POST` request to your configured Bartleby server
and is **not** retained anywhere else by the extension.

## What the extension stores

On its options page you provide two values, which are saved in the browser's
local extension storage (`chrome.storage.local`) on your device:

- the **server URL** of your Bartleby instance; and
- a **bearer token** used to authenticate to that server.

These never leave your device except as the `Authorization` header sent to your
own server. They are not transmitted to any third party.

## Permissions and why they are needed

| Permission | Why |
| --- | --- |
| `activeTab` | Read the current tab's content **only** when you click the extension. |
| `scripting` | Inject the one-off extractor script into that tab to read the article on user action. |
| `storage` | Persist your server URL and bearer token on your device. |
| `contextMenus` | Add a "Open Bartleby server" entry to the toolbar icon's right-click menu. |
| Optional host access to your server's origin | Allow the `POST` to your configured server. Requested at runtime for **only** the origin you enter — never for all sites by default. |

## Data sharing

The extension shares data with **no one**. It does not sell, transfer, or
disclose any data. The data you clip is sent solely to the server you control.

## Data retention and deletion

The extension itself retains nothing beyond the server URL and token in local
storage, which you can clear at any time by removing the values on the options
page or uninstalling the extension. Notes you save live on **your** server;
retention and deletion there are governed by your own Bartleby configuration.

## Contact

Questions or concerns: open an issue at
<https://github.com/t11z/bartleby/issues>.
