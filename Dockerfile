FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependency definition first for layer caching
COPY pyproject.toml uv.lock /app/

# Install dependencies (no dev, no editable install)
RUN uv sync --no-dev --no-install-project --frozen

# Utilisateur non privilegie (UID/GID fixes pour la coherence des volumes)
RUN groupadd --gid 1000 app \
 && useradd --uid 1000 --gid 1000 --create-home --shell /usr/sbin/nologin app

COPY --chown=app:app src/ /app/src/

# Install the project itself
RUN uv sync --no-dev --frozen

USER app

EXPOSE 8000

# Default ES_HOST points at the Docker-compose service name; override when
# running the image standalone.
ENV ES_HOST="http://elasticsearch:9200"

CMD ["uv", "run", "--no-dev", "python", "-m", "mcpdiffusion.server"]
