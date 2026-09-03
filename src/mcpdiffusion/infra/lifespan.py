"""Shared clients, created once at startup and torn down on shutdown."""

import logging
from collections.abc import AsyncIterator, Callable
from typing import Any

from elasticsearch import AsyncElasticsearch
from httpx import AsyncClient, Timeout
from fastmcp.server.lifespan import lifespan

logger = logging.getLogger(__name__)

# insee.fr serves different markup to unknown agents, so the scraper has to look like a browser.
INSEE_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
# The APIs have no such requirement, so they get an honest identity.
MELODI_USER_AGENT = "McpDiffusion/0.1"
SPARQL_USER_AGENT = "MCP-RMeS/2.0"

ES_MAX_RETRIES = 2


def build_lifespan(
    *,
    es_host: str,
    es_tls_verify: bool,
    es_request_timeout_seconds: int,
    insee_base_url: str,
    insee_request_timeout_seconds: int,
    insee_connect_timeout_seconds: int,
    melodi_data_base_url: str,
    melodi_request_timeout_seconds: int,
    melodi_connect_timeout_seconds: int,
) -> Callable[..., Any]:

    @lifespan
    async def app_lifespan(_server: Any) -> AsyncIterator[dict[str, Any]]:
        elasticsearch_client = AsyncElasticsearch(
            es_host,
            verify_certs=es_tls_verify,
            request_timeout=es_request_timeout_seconds,
            max_retries=ES_MAX_RETRIES,
            retry_on_timeout=True,
        )
        logger.info("Elasticsearch client initialized for %s", es_host)

        insee_http_client = AsyncClient(
            base_url=insee_base_url,
            headers={"User-Agent": INSEE_USER_AGENT},
            timeout=Timeout(
                insee_request_timeout_seconds,
                connect=insee_connect_timeout_seconds,
            ),
        )
        logger.info("insee.fr client initialized for %s", insee_base_url)

        melodi_http_client = AsyncClient(
            base_url=melodi_data_base_url,
            headers={"User-Agent": MELODI_USER_AGENT},
            timeout=Timeout(
                melodi_request_timeout_seconds,
                connect=melodi_connect_timeout_seconds,
            ),
        )
        logger.info("MELODI client initialized for %s", melodi_data_base_url)

        # RMES passes its own timeout per query, so this client sets none.
        sparql_http_client = AsyncClient(
            headers={"User-Agent": SPARQL_USER_AGENT},
        )
        logger.info("SPARQL client initialized")

        try:
            yield {
                "elasticsearch_client": elasticsearch_client,
                "insee_http_client": insee_http_client,
                "melodi_http_client": melodi_http_client,
                "sparql_http_client": sparql_http_client,
            }
        finally:
            await elasticsearch_client.close()
            await insee_http_client.aclose()
            await melodi_http_client.aclose()
            await sparql_http_client.aclose()

    return app_lifespan
