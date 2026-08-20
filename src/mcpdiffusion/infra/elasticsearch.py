"""Centralized Elasticsearch client singleton with injected settings."""
from __future__ import annotations

import logging

from elasticsearch import Elasticsearch

from ..config.settings import Settings, get_settings

logger = logging.getLogger("mcp.main")

_client: Elasticsearch | None = None


def get_es_client(settings: Settings | None = None) -> Elasticsearch:
    """Return the shared Elasticsearch client, building it on first call."""
    global _client
    if _client is None:
        s = settings or get_settings()
        if not s.es_host:
            raise RuntimeError(
                "ES_HOST environment variable is not set. "
                "See .env.example for the expected value."
            )
        _client = Elasticsearch(
            s.es_host,
            verify_certs=s.tls_verify,
            request_timeout=30,
            max_retries=2,
            retry_on_timeout=True,
        )
        logger.info("Elasticsearch client initialized for %s", s.es_host)
    return _client


def reset_es_client() -> None:
    """Drop the cached client. Used by tests / long-running reconfiguration."""
    global _client
    _client = None
