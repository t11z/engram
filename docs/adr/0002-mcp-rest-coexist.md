# 0002. MCP, REST, and static UI in one process

- Status: accepted
- Date: 2026-05-23

## Context and problem statement

Engram exposes three surfaces over the same vault: an MCP endpoint for LLM
clients, a REST API for the extension and web UI, and the static web UI bundle.
We must decide whether these run as one process or as separate services. The
target deployment is a single user on their own VPS, so operational simplicity
matters more than independent scaling.

## Considered options

- One FastAPI process mounting REST, MCP (via `mcp.server.fastmcp`), and static
  files together.
- Separate processes/containers per surface behind a reverse proxy.
- REST + static together, MCP as a separate service.

## Decision

Serve all three surfaces from one FastAPI process. REST routes are standard
FastAPI; the MCP endpoint is mounted via the official `mcp` Python SDK; the web
UI bundle is mounted as static files at `/`. All three call into
`packages/core`.

### Rationale

A single process means one deployment unit, one port, one auth configuration, and
one place where the surfaces share the service layer. Splitting into multiple
services would add a reverse proxy, inter-service concerns, and more moving parts
for zero benefit to a single-user deployment. The official MCP SDK supports
mounting alongside a FastAPI app, so coexistence is straightforward.

## Consequences

- Simplest possible deployment: `docker compose up` yields one container serving
  everything.
- REST and MCP share one bearer token and one service layer — consistent behavior
  across surfaces by construction.
- The three surfaces share a process lifecycle and resource pool; this is
  acceptable for one user and revisitable if multi-user ever enters scope (it
  does not in v1).
- The web UI must be built to static assets at image-build time so the server can
  serve it — handled by the multi-stage Dockerfile.
