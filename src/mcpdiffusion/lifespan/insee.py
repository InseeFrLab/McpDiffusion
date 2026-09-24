"""What the insee.fr tools need at runtime."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from elasticsearch import AsyncElasticsearch
from httpx import AsyncClient, Timeout

from ..services.insee.document_service import InseeDocumentService
from ..services.insee.index_service import InseeIndexService

logger = logging.getLogger(__name__)

# insee.fr serves different markup to unknown agents, so the scraper has to look like a browser.
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


@asynccontextmanager
async def insee_lifespan(
    elasticsearch_client: AsyncElasticsearch,
    base_url: str,
    request_timeout_seconds: int,
    connect_timeout_seconds: int,
    publications_index: str,
    document_max_markdown_chars: int,
) -> AsyncIterator[dict[str, Any]]:
    """Build the insee.fr services and close the scraping client on shutdown."""
    http_client = AsyncClient(
        base_url=base_url,
        headers={"User-Agent": USER_AGENT},
        timeout=Timeout(
            request_timeout_seconds,
            connect=connect_timeout_seconds,
        ),
    )
    logger.info("insee.fr client initialized for %s", base_url)
    try:
        yield {
            "insee_index_service": InseeIndexService(
                elasticsearch_client=elasticsearch_client,
                publications_index=publications_index,
            ),
            "insee_document_service": InseeDocumentService(
                http_client=http_client,
                max_markdown_chars=document_max_markdown_chars,
            ),
        }
    finally:
        await http_client.aclose()
