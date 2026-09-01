# ---- Build stage ----
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependency definition first for layer caching
COPY pyproject.toml uv.lock /app/

# Install dependencies (no dev, no editable install)
RUN uv sync --no-dev --no-install-project --frozen

COPY src/ /app/src/

# Install the project itself
RUN uv sync --no-dev --frozen

# ---- Runtime stage ----
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Utilisateur non privilegie (UID/GID fixes pour la coherence des volumes)
RUN groupadd --gid 1000 app \
 && useradd --uid 1000 --gid 1000 --create-home --shell /usr/sbin/nologin app

# Copy only the virtual environment and source from the build stage
COPY --from=builder --chown=app:app /app/.venv /app/.venv
COPY --from=builder --chown=app:app /app/src /app/src

USER app

EXPOSE 8000

# Default ES_HOST points at the Docker-compose service name; override when
# running the image standalone.

CMD ["/app/.venv/bin/python", "-m", "mcpdiffusion.server"]
