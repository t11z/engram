# 0004. Embedded OAuth 2.1 authorization server for the MCP endpoint

- Status: accepted
- Date: 2026-05-24

## Context and problem statement

claude.ai (Web) only adds remote MCP servers as "Custom Connectors" through the
MCP spec's OAuth authorization flow: it performs Dynamic Client Registration and
an authorization-code + PKCE exchange against the server, then stores the issued
token. It has no field for a pre-shared bearer token. Engram until now
authenticated solely with a single static `ENGRAM_AUTH_TOKEN` shared by REST and
MCP ([ADR-0003](./0003-self-hosted-only.md) deferred OAuth explicitly). That
static token cannot be entered into the claude.ai connector UI, so the product
goal "works with claude.ai" was unreachable without OAuth. We need an OAuth flow
that fits the self-hosted, single-container, single-user posture and does not
break the existing static-token clients (REST, web UI, browser extension, MCP
Inspector, Claude Desktop).

## Considered options

- **Embedded authorization server.** Engram issues its own tokens; clients
  self-register via DCR. No external dependency.
- **Delegate to an external IdP** (Auth0, Google, Keycloak, …) and act only as a
  resource server validating its tokens.
- **Static token only** (status quo) — accept that claude.ai is unsupported.

## Decision

Add an **embedded OAuth 2.1 authorization server** to the existing FastAPI app,
built entirely on the OAuth primitives already shipped in the pinned `mcp` SDK
(`create_auth_routes`, `create_protected_resource_routes`,
`OAuthAuthorizationServerProvider`, `TokenVerifier`, and the auth middleware
chain) plus stdlib `sqlite3`. No new runtime dependency.

Three deliberate choices shape it:

1. **Engram is its own issuer** — it mints and verifies its own tokens; clients
   register dynamically (RFC 7591). The user only pastes the `/mcp` URL into
   claude.ai.
2. **A password gate** (`ENGRAM_OAUTH_PASSWORD`) guards a minimal login/consent
   page. DCR is open by spec, so without a gate anyone reaching the public URL
   could mint a token; the password is the human-consent step.
3. **Persistent SQLite store** at `<vault>/.engram/oauth.db`, separate from the
   rebuildable FTS index, so registered clients and live tokens survive restarts
   and claude.ai stays connected.

OAuth is **opt-in**: it activates only when `ENGRAM_PUBLIC_URL` is set (that URL
is the issuer and resource identifier). When unset, the server behaves exactly as
before. When set, `/mcp` accepts **either** an OAuth access token **or** the
static `ENGRAM_AUTH_TOKEN`, preserving every existing client.

### Rationale

The embedded server is the only option that keeps the self-hosted promise of
ADR-0003 intact: no third-party IdP to run or trust, no outbound calls, one
container. Delegating to an external IdP would contradict the data-ownership
premise and add operational burden disproportionate to a single-user tool.
Building on the SDK's own OAuth code (the same pieces FastMCP wires internally)
means we implement a thin provider/store/verifier rather than hand-rolling PKCE,
client authentication, or metadata endpoints. The password gate is the minimum
viable consent mechanism for a single-user server with open DCR.

This evolves — does not overturn — ADR-0003: the project stays single-user and
self-hosted; OAuth is an additional front door to the *same* single vault, not
multi-tenancy. No user table, no accounts; one password, one vault.

## Consequences

- New opt-in config: `ENGRAM_PUBLIC_URL` (enables OAuth, must be the public
  HTTPS origin) and `ENGRAM_OAUTH_PASSWORD` (required whenever the public URL is
  set; the CLI refuses to start otherwise).
- OAuth metadata and endpoints (`/.well-known/oauth-authorization-server`,
  `/.well-known/oauth-protected-resource/mcp`, `/authorize`, `/token`,
  `/register`, `/revoke`, `/oauth/login`) live at the app root so claude.ai can
  discover them; `/mcp` is guarded by the SDK middleware chain that emits the
  `WWW-Authenticate` header pointing at the protected-resource metadata.
- A new SQLite database (`oauth.db`) holds clients and tokens; unlike the FTS
  index it is **not** disposable. It contains secrets and must be backed up /
  protected with the vault.
- Token lifetimes are fixed constants (access ~1 h, refresh ~30 d) rather than
  env vars, to keep the configuration surface small.
- OAuth must be deployed behind HTTPS with a correct `ENGRAM_PUBLIC_URL`; the
  issuer is taken from that value rather than guessed from proxy headers.
- Should finer-grained scopes, multiple users, or token introspection ever be
  wanted, they would extend this provider and warrant their own ADR.
