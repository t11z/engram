# Engram

A self-hosted personal knowledge vault that any LLM can read and write through
the Model Context Protocol.

[![License: MIT](https://img.shields.io/badge/License-MIT-informational.svg)](./LICENSE)
[![CI](https://github.com/t11z/engram/actions/workflows/ci.yml/badge.svg)](https://github.com/t11z/engram/actions/workflows/ci.yml)

Engram keeps your notes as plain Markdown files on a server you control, and
exposes them over three surfaces from a single process: a spec-compliant **MCP**
endpoint for LLM clients, a versioned **REST API** for the browser extension and
web UI, and the **web UI** itself. Your assistant can save what you tell it and
recall it later; you can clip a web page from your browser; you can browse and
read everything from a small UI — all against the same vault.

## Why this exists

The convenient way to give an assistant a memory is to hand your notes to someone
else's server. Engram takes the other path: **you host it, you hold the data.**
There is no hosted instance, no account, no tenant but you. There is no
telemetry and no update pings; the only outbound calls the server makes are the
ones you trigger yourself by sharing a URL into the vault (see [ADR-0005](./docs/adr/0005-server-side-url-fetch.md)),
and the browser extension talks only to the server you point it at. That
single-user, self-hosted posture is the feature, not a limitation: your
knowledge vault stays a directory of Markdown files on your own machine that
you can read, back up, and move with ordinary tools, whether or not Engram is
running.

## Live demo

**▶ [Try the web UI in your browser](https://t11z.github.io/engram/demo/)** — a
static demo with built-in sample data, no install or server required. Everything
runs locally in your browser and resets on reload.

## Quick start

You need Docker and a bearer token of your choosing (any long random string).

```bash
git clone https://github.com/t11z/engram.git
cd engram/infra
cp .env.example .env
# edit .env: set ENGRAM_AUTH_TOKEN to a long random secret
docker compose up -d
```

Then open <http://localhost:8080/> for the web UI, and point your MCP client at
`http://localhost:8080/mcp` using the same token. Put it behind HTTPS before
exposing it to the internet — see [`infra/Caddyfile.example`](./infra/Caddyfile.example)
and the [installation guide](https://t11z.github.io/engram/installation/).

## Architecture

One backend process serves all three surfaces and reads/writes a single vault of
Markdown files.

```mermaid
flowchart LR
  L[LLM client] -->|MCP| S
  E[Browser extension] -->|REST + bearer| S
  W[Web UI] -->|REST + bearer| S
  I_OS[iOS Shortcut] -->|REST + bearer| S
  S[Engram server] --> V[(Vault: Markdown + YAML on disk)]
  S --- I[(SQLite FTS5 index)]
```

To share a URL from Safari on iPhone, see [`docs/ios-shortcut.md`](./docs/ios-shortcut.md).

The full design — data model, API, storage, and roadmap — is in
[`docs/IMPLEMENTATION_PLAN.md`](./docs/IMPLEMENTATION_PLAN.md).

## Client compatibility

The MCP server is spec-compliant and works with any MCP-capable client. It is
**tested primarily with Claude**. If you find an incompatibility with another
MCP client, please file an issue.

## Documentation

Full docs — installation, configuration reference, MCP tool reference, and API
reference — live at **<https://t11z.github.io/engram/>**.

## Contributing and security

- Contributions are welcome — see [`CONTRIBUTING.md`](./CONTRIBUTING.md).
- To report a vulnerability, see [`SECURITY.md`](./SECURITY.md).

## License

[MIT](./LICENSE) © Thomas Sprock.
