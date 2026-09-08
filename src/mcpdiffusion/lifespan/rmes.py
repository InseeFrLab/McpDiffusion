"""What the RMES tools need at runtime."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from httpx import AsyncClient

from ..services.rmes.graph_store_service import RmesGraphStoreService

logger = logging.getLogger(__name__)

# Honest identity -- these APIs need no browser spoofing. Hardcoded: bump with pyproject.toml maybe.
USER_AGENT = "McpDiffusion/0.1.0"


@asynccontextmanager
async def rmes_lifespan(
    sparql_endpoint_url: str,
    graph_base_uri: str,
    graph_listing_timeout_seconds: float,
    graph_listing_max_rows: int,
    graph_cache_ttl_seconds: float,
) -> AsyncIterator[dict[str, Any]]:
    """Build the RMES service and close its client on shutdown.

    RMES passes its own timeout per query, so this client sets none.
    """
    http_client = AsyncClient(headers={"User-Agent": USER_AGENT})
    logger.info("SPARQL client initialized")
    try:
        yield {
            "rmes_graph_store_service": RmesGraphStoreService(
                http_client=http_client,
                sparql_endpoint_url=sparql_endpoint_url,
                graph_base_uri=graph_base_uri,
                graph_listing_timeout_seconds=graph_listing_timeout_seconds,
                graph_listing_max_rows=graph_listing_max_rows,
                graph_cache_ttl_seconds=graph_cache_ttl_seconds,
            ),
        }
    finally:
        await http_client.aclose()
