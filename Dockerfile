FROM python:3.12-slim

WORKDIR /app
COPY mcpdiffusion/ /app/mcpdiffusion/

RUN pip install --no-cache-dir -r /app/mcpdiffusion/requirements.txt

EXPOSE 8000

CMD ["python", "/app/mcpdiffusion/server.py"]