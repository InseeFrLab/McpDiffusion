"""
Centralized Elasticsearch client and index-name constants.

Why a module-level singleton:
- Tools used to each build their own `Elasticsearch(...)` at import time.
  That made the whole server refuse to start when ES was down, even though
  one tool (`query_insee_rmes`) doesn't need ES at all.
- This module builds the client lazily on first `get_es_client()` call,
  and tools catch ES connection errors so a backend outage degrades to
  a structured tool error instead of a boot failure.

Configuration:
- `ES_HOST` (required) -- single endpoint URL, e.g. http://localhost:9200.
- `TLS_VERIFY` -- "true" (default) or "false".
- Credentials are intentionally NOT supported; rely on network-level auth.
  Add basic_auth here if that assumption changes.
"""
from __future__ import annotations

import logging
import os

from elasticsearch import Elasticsearch


logger = logging.getLogger("mcp.main")

# Index names -- kept as constants so they can be overridden from env if needed.
INDEX_PRODUITS = os.getenv("ES_INDEX_PRODUITS", "produit")
INDEX_MELODI_DATASETS = os.getenv("ES_INDEX_MELODI_DATASETS", "melodi_datasets")
INDEX_MELODI_COLUMNS = os.getenv("ES_INDEX_MELODI_COLUMNS", "melodi_columns")


_client: Elasticsearch | None = None


def _tls_verify() -> bool:
    return os.getenv("TLS_VERIFY", "true").strip().lower() != "false"


def get_es_client() -> Elasticsearch:
    """Return the shared Elasticsearch client, building it on first call."""
    global _client
    if _client is None:
        host = os.getenv("ES_HOST")
        if not host:
            raise RuntimeError(
                "ES_HOST environment variable is not set. "
                "See .env.example for the expected value."
            )
        _client = Elasticsearch(
            host,
            verify_certs=_tls_verify(),
            request_timeout=30,
            max_retries=2,
            retry_on_timeout=True,
        )
        logger.info("Elasticsearch client initialized for %s", host)
    return _client


def reset_es_client() -> None:
    """Drop the cached client. Used by tests / long-running reconfiguration."""
    global _client
    _client = None
