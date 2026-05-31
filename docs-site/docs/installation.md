# Installation

Engram is a single container that serves MCP, REST, and the web UI on one port.
Pick the deployment that fits you.

## Option A — docker-compose (recommended)

See the [quick start](quick-start.md). The compose file in `infra/` pulls
`ghcr.io/t11z/engram:latest` and mounts a named volume for the vault. To build
from source instead, uncomment the `build:` block in `infra/docker-compose.yml`.

## Option B — systemd on bare metal

Use `infra/engram.service` to run the container under systemd:

```bash
sudo mkdir -p /etc/engram /var/lib/engram
sudo cp infra/.env.example /etc/engram/engram.env   # then edit it
sudo cp infra/engram.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now engram
```

## Putting it behind HTTPS

Engram ships no TLS of its own — terminate TLS at a reverse proxy.
`infra/Caddyfile.example` is a complete starting point; Caddy obtains and renews
certificates automatically:

```caddy
engram.example.com {
	encode zstd gzip
	reverse_proxy engram:8080
}
```

## Connecting clients

- **MCP client (e.g. Claude Desktop, MCP Inspector):** add an MCP server pointing
  at `https://your-host/mcp` and supply your `ENGRAM_AUTH_TOKEN` via the
  client's standard auth mechanism.
- **claude.ai (Web) Custom Connector:** claude.ai cannot store a static token, so
  enable OAuth — set `ENGRAM_PUBLIC_URL` (your public HTTPS origin) and
  `ENGRAM_OAUTH_PASSWORD`, then in claude.ai go to **Settings → Connectors → Add
  custom connector** and paste `https://your-host/mcp`. claude.ai self-registers,
  redirects you to a login page where you enter the OAuth password, and is then
  connected. See [Configuration → OAuth for claude.ai](configuration.md#oauth-for-claudeai-optional).
- **Web UI:** browse to `https://your-host/`.
- **Browser extension:** install it, open its options page, and set the server
  URL and the same token.

## Verifying

```bash
curl https://your-host/healthz          # -> {"status":"ok", ...}
curl -H "Authorization: Bearer $TOKEN" https://your-host/api/v1/notes
```
