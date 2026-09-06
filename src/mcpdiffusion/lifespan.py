"""Shared clients, created once at startup and torn down on shutdown."""

import logging
from collections.abc import AsyncIterator, Callable
from typing import Any

from elasticsearch import AsyncElasticsearch
from fastmcp.server.lifespan import lifespan
from httpx import AsyncClient, Timeout

from .services.insee.document_service import InseeDocumentService
from .services.insee.index_service import InseeIndexService
from .services.melodi.api_service import MelodiApiService
from .services.melodi.index_service import MelodiIndexService
from .services.rmes.graph_store_service import RmesGraphStoreService

logger = logging.getLogger(__name__)

# insee.fr serves different markup to unknown agents, so the scraper has to look like a browser.
INSEE_USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
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
    melodi_datasets_index: str,
    melodi_columns_index: str,
    insee_publications_index: str,
    rmes_sparql_endpoint_url: str,
    rmes_graph_base_uri: str,
    rmes_graph_listing_timeout_seconds: float,
    rmes_graph_listing_max_rows: int,
    rmes_graph_cache_ttl_seconds: float,
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

        # Services bind a client to its index or base URL once, so nothing downstream has to
        # carry an index name around. They hold no request state, so one instance serves every call.
        melodi_index_service = MelodiIndexService(
            elasticsearch_client=elasticsearch_client,
            datasets_index=melodi_datasets_index,
            columns_index=melodi_columns_index,
        )
        melodi_api_service = MelodiApiService(http_client=melodi_http_client)
        insee_index_service = InseeIndexService(
            elasticsearch_client=elasticsearch_client,
            publications_index=insee_publications_index,
        )
        insee_document_service = InseeDocumentService(http_client=insee_http_client)
        rmes_graph_store_service = RmesGraphStoreService(
            http_client=sparql_http_client,
            sparql_endpoint_url=rmes_sparql_endpoint_url,
            graph_base_uri=rmes_graph_base_uri,
            graph_listing_timeout_seconds=rmes_graph_listing_timeout_seconds,
            graph_listing_max_rows=rmes_graph_listing_max_rows,
            graph_cache_ttl_seconds=rmes_graph_cache_ttl_seconds,
        )

        try:
            yield {
                "elasticsearch_client": elasticsearch_client,
                "insee_http_client": insee_http_client,
                "melodi_http_client": melodi_http_client,
                "sparql_http_client": sparql_http_client,
                "melodi_index_service": melodi_index_service,
                "melodi_api_service": melodi_api_service,
                "insee_index_service": insee_index_service,
                "insee_document_service": insee_document_service,
                "rmes_graph_store_service": rmes_graph_store_service,
            }
        finally:
            await elasticsearch_client.close()
            await insee_http_client.aclose()
            await melodi_http_client.aclose()
            await sparql_http_client.aclose()

    return app_lifespan
