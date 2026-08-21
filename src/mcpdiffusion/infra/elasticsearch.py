"""Centralized Elasticsearch client singleton with injected settings."""

from __future__ import annotations
from fastmcp.server.lifespan import lifespan
from fastmcp import Context
from elasticsearch import Elasticsearch
from ..config.settings import get_settings
import logging

logger = logging.getLogger("mcp.main")

@lifespan
async def build_es_client(server):
    s = get_settings()
    if not s.es_host:
        raise RuntimeError("ES_HOST is not set. See .env.example.")
    client = Elasticsearch(
        s.es_host, verify_certs=s.tls_verify,
        request_timeout=30, max_retries=2, retry_on_timeout=True,
    )
    logger.info("Elasticsearch client initialized for %s", s.es_host)
    yield {"es_client": client}
    
    await client.close()


def get_client_es(ctx : Context) :
    return ctx.lifespan_context["es_client"]