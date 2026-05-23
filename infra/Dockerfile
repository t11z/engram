# Bartleby — single image containing the server + the prebuilt web UI.
# Multi-stage: (1) build the SvelteKit UI to static assets, (2) assemble the
# Python server and copy the UI bundle in. The final image serves MCP, REST,
# and the UI on one port.
#
# NOTE: paths below assume the repo layout in docs/IMPLEMENTATION_PLAN.md. This
# Dockerfile is built on release tags once the application code exists.

# --- Stage 1: build the web UI -------------------------------------------------
FROM node:26-slim AS ui
WORKDIR /app
RUN corepack enable
COPY pnpm-workspace.yaml package.json pnpm-lock.yaml ./
COPY apps/web-ui/package.json apps/web-ui/package.json
COPY packages/contract packages/contract
RUN pnpm install --frozen-lockfile --filter web-ui...
COPY apps/web-ui apps/web-ui
RUN pnpm --filter web-ui build   # -> apps/web-ui/build (static adapter)

# --- Stage 2: assemble the server ---------------------------------------------
FROM python:3.12-slim AS runtime
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    BARTLEBY_VAULT_PATH=/data/vault \
    BARTLEBY_HOST=0.0.0.0 \
    BARTLEBY_PORT=8080

WORKDIR /app

# Install dependencies first for better layer caching.
COPY pyproject.toml uv.lock ./
COPY packages/core packages/core
COPY apps/server apps/server
RUN uv sync --frozen --no-dev

# Bring in the prebuilt UI so the server can serve it at "/".
COPY --from=ui /app/apps/web-ui/build apps/web-ui/build

RUN useradd --system --uid 10001 bartleby \
    && mkdir -p /data/vault \
    && chown -R bartleby:bartleby /app /data
USER bartleby

EXPOSE 8080
VOLUME ["/data"]

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s \
  CMD python -c "import urllib.request,os,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('BARTLEBY_PORT','8080')+'/healthz').status==200 else 1)"

CMD ["uv", "run", "bartleby"]
