FROM python:3.12-slim

WORKDIR /app
COPY mcpdiffusion/ /app/mcpdiffusion/

RUN pip install --no-cache-dir -r /app/mcpdiffusion/requirements.txt

EXPOSE 8000

# Default ES_HOST points at the Docker-compose service name; override when
# running the image standalone.
ENV ES_HOST="http://elasticsearch:9200"

CMD ["python", "/app/mcpdiffusion/server.py"]
