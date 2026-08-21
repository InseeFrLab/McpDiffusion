"""FastMCP entrypoint for the mcp-diffusion server.

Boots Uvicorn, registers every tool via `tools.register_tools(mcp)`,
and exposes the HTTP transport on MCP_HOST:MCP_PORT.
"""
from __future__ import annotations

import logging
import sys

from dotenv import load_dotenv
from fastmcp import FastMCP
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .config.settings import get_settings
from .core.logging import MAIN_LOGGER_NAME, UVICORN_LOGGING_CONFIG
from .core.middleware import RateLimitMiddleware
from .tools import register_tools
from .infra.elasticsearch import build_es_client

load_dotenv()

settings = get_settings()
logger = logging.getLogger(MAIN_LOGGER_NAME)

mcp = FastMCP("INSEE-mcp-diffusion", lifespan = build_es_client )

register_tools(mcp, toollist=settings.toollist)

app = mcp.http_app()

# TrustedHostMiddleware
_allowed_hosts_raw = settings.allowed_hosts.strip()
_allowed_hosts = (
    ["*"] if _allowed_hosts_raw == "*"
    else [h.strip() for h in _allowed_hosts_raw.split(",") if h.strip()]
)
if _allowed_hosts == ["*"]:
    logger.warning(
        "TrustedHostMiddleware configured with allowed_hosts=['*']. "
        "Set ALLOWED_HOSTS before exposing the server publicly."
    )
app.add_middleware(TrustedHostMiddleware, allowed_hosts=_allowed_hosts)
app.add_middleware(RateLimitMiddleware, settings=settings)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=settings.mcp_host,
        port=settings.mcp_port,
        proxy_headers=True,
        forwarded_allow_ips=settings.forwarded_allow_ips,
        log_level="info",
        log_config=UVICORN_LOGGING_CONFIG,
    )
