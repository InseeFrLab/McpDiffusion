"""The Elasticsearch client, shared by the insee.fr and Melodi searches."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from elasticsearch import AsyncElasticsearch

logger = logging.getLogger(__name__)

MAX_RETRIES = 2


@asynccontextmanager
async def elasticsearch_lifespan(
    host: str,
    tls_verify: bool,
    request_timeout_seconds: int,
) -> AsyncIterator[AsyncElasticsearch]:
    """Open the shared client and close it on shutdown.

    Construction opens no connection, so a wrong host surfaces on the first search, not here.
    """
    client = AsyncElasticsearch(
        host,
        verify_certs=tls_verify,
        request_timeout=request_timeout_seconds,
        max_retries=MAX_RETRIES,
        retry_on_timeout=True,
    )
    logger.info("Elasticsearch client initialized for %s", host)
    try:
        yield client
    finally:
        await client.close()
