"""Shared HTTP client factory with centralized TLS settings."""
from __future__ import annotations

import httpx

from ..config.settings import Settings, get_settings


_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
_DEFAULT_TIMEOUT = httpx.Timeout(30.0, connect=10.0)


def create_async_client(
    *,
    settings: Settings | None = None,
    headers: dict[str, str] | None = None,
    follow_redirects: bool = False,
    timeout: httpx.Timeout | None = None,
) -> httpx.AsyncClient:
    """Create an httpx.AsyncClient with centralized TLS and timeout settings."""
    s = settings or get_settings()
    merged_headers = {"User-Agent": _USER_AGENT}
    if headers:
        merged_headers.update(headers)
    return httpx.AsyncClient(
        verify=s.tls_verify,
        headers=merged_headers,
        follow_redirects=follow_redirects,
        timeout=timeout or _DEFAULT_TIMEOUT,
    )
