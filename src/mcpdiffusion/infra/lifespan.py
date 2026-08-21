"""Combined application lifespan: creates and tears down shared clients."""
from __future__ import annotations

import logging

import httpx
from elasticsearch import Elasticsearch
from fastmcp.server.lifespan import lifespan

from ..config.settings import get_settings

logger = logging.getLogger("mcp.main")

_HTTP_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
_HTTP_TIMEOUT = httpx.Timeout(30.0, connect=10.0)
_SPARQL_USER_AGENT = "MCP-RMeS/2.0"


@lifespan
async def app_lifespan(server):
    s = get_settings()

    # Elasticsearch
    if not s.es_host:
        raise RuntimeError("ES_HOST is not set. See .env.example.")
    es_client = Elasticsearch(
        s.es_host,
        verify_certs=s.tls_verify,
        request_timeout=30,
        max_retries=2,
        retry_on_timeout=True,
    )
    logger.info("Elasticsearch client initialized for %s", s.es_host)

    # HTTP client (insee.fr, melodi API)
    http_client = httpx.AsyncClient(
        verify=s.tls_verify,
        headers={"User-Agent": _HTTP_USER_AGENT},
        timeout=_HTTP_TIMEOUT,
    )
    logger.info("HTTP client initialized")

    # SPARQL client
    sparql_client = httpx.AsyncClient(
        headers={"User-Agent": _SPARQL_USER_AGENT},
    )
    logger.info("SPARQL client initialized")

    yield {
        "es_client": es_client,
        "http_client": http_client,
        "sparql_client": sparql_client,
    }

    await es_client.close()
    await http_client.aclose()
    await sparql_client.aclose()
