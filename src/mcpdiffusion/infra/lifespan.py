"""Combined application lifespan: creates and tears down shared clients."""
from __future__ import annotations

import logging

import httpx
from elasticsearch import Elasticsearch
from fastmcp.server.lifespan import lifespan

from ..config.settings import get_settings

# Fixme: was there not a reference for that logger name in 'config/logging.py'?
logger = logging.getLogger("mcp.main")

_HTTP_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
_HTTP_TIMEOUT = httpx.Timeout(30.0, connect=10.0)
_SPARQL_USER_AGENT = "MCP-RMeS/2.0"

# Fixme: One issue I see with that pattern is that if some client instantiation fail,
#   the error is ignored and this can be tricky to identify
# Fixme: Also, i see no client is properly tested upon creation (simple ping).
#   It could help identify issues at startup: but this is not mandatory
# Fixme: this piece of code contains too many magic values that belong in settings
# Fixme: server is unused, if required by FastMCP, prefer prefixing it with an underscore
@lifespan
async def app_lifespan(server):
    # Fixme: I am questioning whether this should be the responsibility of that function to instantiate settings
    s = get_settings()

    # Elasticsearch
    # Fixme: in 'config/settings.py', 'es_host' is deemed optional, so it must be made mandatory if required here
    if not s.es_host:
        raise RuntimeError("ES_HOST is not set. See .env.example.")

    # Fixme: if this synchronous client is used within async coroutines,
    #  it will block the event loop for the duration of the query
    #   This is a major issue
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
    # Fixme: TLS is ignored in some clients which seems inconsistent
    sparql_client = httpx.AsyncClient(
        headers={"User-Agent": _SPARQL_USER_AGENT},
    )
    logger.info("SPARQL client initialized")

    yield {
        "es_client": es_client,
        "http_client": http_client,
        "sparql_client": sparql_client,
    }

    # Fixme: the instantiated elastic client is synchronous, so cannot be prepended by the 'await' keyword
    #   this would app to raise and crash on shutdown
    await es_client.close()
    await http_client.aclose()
    await sparql_client.aclose()
