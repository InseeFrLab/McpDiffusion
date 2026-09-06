"""What the Melodi tools need at runtime."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from elasticsearch import AsyncElasticsearch
from httpx import AsyncClient, Timeout

from ..services.melodi.api_service import MelodiApiService
from ..services.melodi.index_service import MelodiIndexService

logger = logging.getLogger(__name__)

# The API has no browser requirement, so it gets an honest identity.
USER_AGENT = "McpDiffusion/0.1"


@asynccontextmanager
async def melodi_lifespan(
    elasticsearch_client: AsyncElasticsearch,
    data_base_url: str,
    request_timeout_seconds: int,
    connect_timeout_seconds: int,
    datasets_index: str,
    columns_index: str,
) -> AsyncIterator[dict[str, Any]]:
    """Build the Melodi services and close the API client on shutdown."""
    http_client = AsyncClient(
        base_url=data_base_url,
        headers={"User-Agent": USER_AGENT},
        timeout=Timeout(
            request_timeout_seconds,
            connect=connect_timeout_seconds,
        ),
    )
    logger.info("MELODI client initialized for %s", data_base_url)
    try:
        yield {
            "melodi_index_service": MelodiIndexService(
                elasticsearch_client=elasticsearch_client,
                datasets_index=datasets_index,
                columns_index=columns_index,
            ),
            "melodi_api_service": MelodiApiService(http_client=http_client),
        }
    finally:
        await http_client.aclose()
