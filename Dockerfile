# Multi-stage: the builder installs the dependencies, the runtime keeps only the result. The uv
# binary and the download caches never reach the image that ships.

# ---- Build stage ----------------------------------------------------------------------------------
FROM python:3.12-slim AS builder

# UV_LINK_MODE: uv hard-links from its cache into the venv, and hard links cannot cross filesystems.
# The cache mount below is a different mount, so uv would warn on every build. Copy instead.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Pinned rather than :latest -- a build stage that changes under you is not reproducible.
COPY --from=ghcr.io/astral-sh/uv:0.12.5 /uv /uvx /bin/

# Dependencies before source: a one-line code edit must not invalidate the layer that installs them.
COPY pyproject.toml uv.lock /app/

# The cache mount survives between builds without being stored in the image.
# --locked fails when uv.lock is not current for pyproject.toml. Plain `uv sync` would rewrite the
# lock and install versions nobody tested; --frozen would use a stale lock and silently omit a
# dependency that was added but never locked.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev --no-install-project --locked

COPY src/ /app/src/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev --locked

# ---- Runtime stage --------------------------------------------------------------------------------
FROM python:3.12-slim

# CI passes the real version; `dev` is honest for a local build.
ARG APP_VERSION=dev

LABEL org.opencontainers.image.title="McpDiffusion" \
      org.opencontainers.image.description="MCP server exposing INSEE public data to LLM clients" \
      org.opencontainers.image.source="https://github.com/InseeFrLab/McpDiffusion" \
      org.opencontainers.image.version="${APP_VERSION}" \
      org.opencontainers.image.licenses="Apache-2.0"

# PATH: `python` means the venv's python everywhere -- CMD, HEALTHCHECK, and docker exec.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:${PATH}"

WORKDIR /app

# Fixed UID/GID so a bind-mounted file keeps the same owner on the host.
RUN groupadd --gid 1000 app \
 && useradd --uid 1000 --gid 1000 --create-home --shell /usr/sbin/nologin app

# --chown during the copy, never a later chown: that would duplicate every file into a new layer.
COPY --from=builder --chown=app:app /app/.venv /app/.venv
COPY --from=builder --chown=app:app /app/src /app/src

USER app

EXPOSE 8000

# A TCP connect, not an HTTP request: the MCP endpoint answers 400 without a session handshake, so an
# HTTP check would fail on a healthy server. The start period covers the lifespan opening its clients.
HEALTHCHECK --interval=15s --timeout=3s --start-period=20s --retries=3 \
    CMD python -c "import os, socket; socket.create_connection(('127.0.0.1', int(os.environ.get('MCP_PORT', 8000))), 2).close()"

# Exec form: the process runs as PID 1 and receives SIGTERM, so shutdown is clean.
CMD ["python", "-m", "mcpdiffusion.server"]
