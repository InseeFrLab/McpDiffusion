"""Client identity for rate limiting."""

import logging

from fastmcp.server.dependencies import get_http_request
from fastmcp.server.middleware.middleware import MiddlewareContext

logger = logging.getLogger(__name__)

UNKNOWN_CLIENT = "unknown"


def resolve_client_host(_context: MiddlewareContext) -> str:
    """Rate-limit key. Only as trustworthy as `trusted_proxy_hosts`: widen that and a caller can forge it.

    All callers without a resolvable host share one bucket, so a transport that never carries an HTTP
    request would rate-limit every client together. The middleware context is unused -- it is part of
    the `get_client_id` signature, not something this resolver needs.
    """
    try:
        client = get_http_request().client
    except RuntimeError:
        client = None
    if client is None:
        logger.debug("No client address available; this caller shares the fallback rate-limit bucket.")
        return UNKNOWN_CLIENT
    return client.host
