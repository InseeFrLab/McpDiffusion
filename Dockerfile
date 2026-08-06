FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dépendances d'abord : cette couche est mise en cache tant que
# requirements.txt ne change pas.
COPY mcpdiffusion/requirements.txt /app/mcpdiffusion/requirements.txt
RUN pip install --no-cache-dir -r /app/mcpdiffusion/requirements.txt

# Utilisateur non privilégié (UID/GID fixes pour la cohérence des volumes)
RUN groupadd --gid 1000 app \
 && useradd --uid 1000 --gid 1000 --create-home --shell /usr/sbin/nologin app

COPY --chown=app:app mcpdiffusion/ /app/mcpdiffusion/

USER app

EXPOSE 8000

# Default ES_HOST points at the Docker-compose service name; override when
# running the image standalone.
ENV ES_HOST="http://elasticsearch:9200"

CMD ["python", "/app/mcpdiffusion/server.py"]