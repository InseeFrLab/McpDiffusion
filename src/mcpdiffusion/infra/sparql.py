"""Low-level SPARQL HTTP client for RMES."""
from __future__ import annotations

import httpx

from ..config.settings import Settings, get_settings

HEADERS_BASE = {"User-Agent": "MCP-RMeS/2.0"}

_client: httpx.AsyncClient | None = None


def get_sparql_client(settings: Settings | None = None) -> httpx.AsyncClient:
    """Return a shared httpx.AsyncClient for SPARQL queries, recreated if closed."""
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(headers=HEADERS_BASE)
    return _client


def reset_sparql_client() -> None:
    """Drop the cached client. Used by tests."""
    global _client
    _client = None
