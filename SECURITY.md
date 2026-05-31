# Security Policy

Engram is a single-maintainer hobby project. Security reports are taken
seriously, but please set expectations accordingly: responses are **best-effort,
typically within two weeks**. There is no SLA and no bug-bounty program.

## Reporting a vulnerability

Please report vulnerabilities **privately** via GitHub's private vulnerability
reporting:

1. Go to the repository's **Security** tab.
2. Click **Report a vulnerability** (this opens a private advisory only the
   maintainer can see).
3. Include affected component and version, a description, reproduction steps, and
   impact.

Do **not** open a public issue for a suspected vulnerability, and do not include
secrets or the contents of your vault in a report.

Please give a reasonable window to address the issue before any public
disclosure.

## Scope

**In scope** — the code in this repository:

- the server (`apps/server`, `packages/core`, `packages/contract`),
- the browser extension (`apps/extension`),
- the web UI (`apps/web-ui`),
- the deployment artifacts in `infra/`.

**Out of scope:**

- The contents of your own vault. Engram stores the Markdown you give it; it
  does not sanitize or vet that content.
- Third-party MCP clients (Claude, other assistants) and their behavior.
- Misconfiguration of your own deployment — for example, exposing the server
  without HTTPS, or using a weak `ENGRAM_AUTH_TOKEN`. See the
  [installation guide](https://t11z.github.io/engram/installation/) for the
  recommended setup.
- Third-party dependencies — please report those upstream (Dependabot tracks
  them here).

## Security posture

By design, Engram reduces its own attack surface:

- **No outbound calls.** The server never phones home — no telemetry, no update
  checks, no analytics.
- **The extension** makes no outbound calls except to the server URL you
  configure.
- **Single shared bearer token** for REST and MCP, supplied via environment
  variable and never logged. Run behind HTTPS.

## Supported versions

As a pre-1.0 project, only the latest released version receives fixes.
