<p class="engram-hero">
  <img class="engram-hero-mark" src="assets/engram-logomark.svg" alt="Engram" width="112" height="113">
</p>

# Engram

*Your memory, in plain Markdown — readable by any model.*

Engram is a self-hosted personal knowledge vault that any LLM can read and
write through the [Model Context Protocol](https://modelcontextprotocol.io). Your
notes are plain Markdown files on a server you control. One process exposes three
surfaces over the same vault:

- **MCP** at `/mcp` — for LLM clients (Claude and any other MCP-capable client).
- **REST** at `/api/v1` — for the browser extension and web UI.
- **Web UI** at `/` — browse and read your vault.

!!! tip "Try the web UI now"

    See the interface without installing anything: the
    [**live demo**](https://t11z.github.io/engram/demo/) runs the real web UI
    against built-in sample data, entirely in your browser. Nothing is sent
    anywhere; changes reset on reload.

## Why self-hosted

The convenient way to give an assistant a memory is to hand your notes to someone
else's server. Engram takes the other path: you host it, you hold the data.
There is no hosted instance and no account — one user, one server. The server
makes no outbound calls: no telemetry, no update checks. Your vault stays a
directory of Markdown files you can read, back up, and move with ordinary tools.

## Get started

- [Quick start](quick-start.md) — running in a few minutes with docker-compose.
- [Installation](installation.md) — full setup, HTTPS, and connecting clients.
- [Configuration](configuration.md) — every environment variable.
- [MCP tools](mcp-tools.md) and [API reference](api-reference.md).

## Project status

Pre-1.0 and under active development. The design and roadmap are in the
[implementation plan](https://github.com/t11z/engram/blob/main/docs/IMPLEMENTATION_PLAN.md).
The MCP server is spec-compliant and tested primarily with Claude; please file an
issue if another MCP client misbehaves.
