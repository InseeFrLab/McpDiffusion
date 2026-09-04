"""Entrypoint: builds the settings, the clients and the MCP application, then serves it over HTTP."""

import logging

from fastmcp import FastMCP
from fastmcp.server.middleware.error_handling import ErrorHandlingMiddleware
from fastmcp.server.middleware.logging import LoggingMiddleware
from fastmcp.server.middleware.rate_limiting import SlidingWindowRateLimitingMiddleware
from fastmcp.server.middleware.timing import TimingMiddleware

from .config.settings import load_settings
from .core.logging import build_logging_config, configure_logging
from .core.rate_limiting import resolve_client_host
from .infra.lifespan import build_lifespan
from .tools import register_tools

settings = load_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)

mcp = FastMCP(
    "INSEE-mcp-diffusion",
    # Only AppToolError messages reach the caller; anything else is a bug and is replaced
    # by a generic message.
    mask_error_details=True,
    lifespan=build_lifespan(
        es_host=settings.es_host,
        es_tls_verify=settings.es_tls_verify,
        es_request_timeout_seconds=settings.es_request_timeout_seconds,
        insee_base_url=settings.insee_base_url,
        insee_request_timeout_seconds=settings.insee_request_timeout_seconds,
        insee_connect_timeout_seconds=settings.insee_connect_timeout_seconds,
        melodi_data_base_url=settings.melodi_data_base_url,
        melodi_request_timeout_seconds=settings.melodi_request_timeout_seconds,
        melodi_connect_timeout_seconds=settings.melodi_connect_timeout_seconds,
    ),
)

register_tools(mcp, settings)

# Order matters: error handling first so it sees the whole chain, logging last so it records what ran.
# Each middleware logs under its own `fastmcp.*` logger; set levels there to tune the output.
# None of them logs how many results a tool returned. If empty results become hard to diagnose, add an
# `on_call_tool` middleware that inspects the ToolResult, or have the tool report it with `ctx.info`.
mcp.add_middleware(
    # transform_errors would promote our ToolErrors to JSON-RPC protocol errors labelled
    # "Internal error", losing is_error and the message the LLM is meant to act on. We only
    # want the logging and error counting.
    ErrorHandlingMiddleware(transform_errors=False),
)
mcp.add_middleware(
    SlidingWindowRateLimitingMiddleware(
        max_requests=settings.rate_limit_max_requests,
        window_minutes=settings.rate_limit_window_minutes,
        get_client_id=resolve_client_host,
    ),
)
mcp.add_middleware(
    TimingMiddleware(),
)
mcp.add_middleware(
    LoggingMiddleware(),
)

if settings.allowed_hosts == ["*"]:
    logger.warning("allowed_hosts is ['*']. Set ALLOWED_HOSTS before exposing the server publicly.")

app = mcp.http_app(
    host_origin_protection="auto",
    allowed_hosts=settings.allowed_hosts,
)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=settings.mcp_host,
        port=settings.mcp_port,
        proxy_headers=True,
        forwarded_allow_ips=settings.trusted_proxy_hosts,
        log_config=build_logging_config(settings.log_level),
    )
