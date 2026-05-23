# Quick start

You need Docker and a bearer token of your choosing (any long random string).

```bash
git clone https://github.com/t11z/bartleby.git
cd bartleby/infra
cp .env.example .env
# edit .env and set BARTLEBY_AUTH_TOKEN to a long random secret, e.g.:
#   openssl rand -hex 32
docker compose up -d
```

This binds to `127.0.0.1:8080` by default. Then:

- Open <http://localhost:8080/> for the web UI.
- Point your MCP client at `http://localhost:8080/mcp` using the same token.
- Check health: `curl http://localhost:8080/healthz`.

!!! warning "Before exposing it to the internet"
    Put Bartleby behind HTTPS and use a strong token. See
    [Installation](installation.md) for a reverse-proxy setup.

## Next steps

- [Installation](installation.md) — HTTPS, systemd, and connecting clients.
- [Configuration](configuration.md) — all environment variables.
