"""FastMCP entrypoint for the mcp-diffusion server.

Boots Uvicorn, registers every tool via `tools.register_tools(mcp)`,
and exposes the HTTP transport on MCP_HOST:MCP_PORT.
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path  # noqa: F401 (kept for future config discovery)

from dotenv import load_dotenv
from fastmcp import FastMCP
from starlette.middleware.trustedhost import TrustedHostMiddleware

from helpers.logging import MAIN_LOGGER_NAME, UVICORN_LOGGING_CONFIG
from tools import register_tools


load_dotenv()

logger = logging.getLogger(MAIN_LOGGER_NAME)

# FastMCP 3.x accepts transport_security directly; wiring it here makes the
# DNS-rebinding guard opt-in via an environment variable rather than silently
# disabled in source. Default remains off for local dev -- production MUST set
# ENABLE_DNS_REBINDING_PROTECTION=true.
try:
    from mcp.server.transport_security import TransportSecuritySettings
    _transport_security = TransportSecuritySettings(
        enable_dns_rebinding_protection=(
            os.getenv("ENABLE_DNS_REBINDING_PROTECTION", "false").lower() == "true"
        )
    )
    _mcp_kwargs = {"transport_security": _transport_security}
except Exception:
    # Older/newer FastMCP where the class is not importable -- fall back to
    # the legacy constructor. Log so an ops team notices.
    logger.warning(
        "TransportSecuritySettings unavailable; running FastMCP with defaults."
    )
    _mcp_kwargs = {}

mcp = FastMCP("mcp-INSEE", **_mcp_kwargs)

register_tools(mcp)

app = mcp.http_app()

# TrustedHostMiddleware: default permits any host. In production, set
# ALLOWED_HOSTS to a comma-separated list behind your reverse proxy.
_allowed_hosts_raw = os.getenv("ALLOWED_HOSTS", "*").strip()
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


if __name__ == "__main__":
    import uvicorn

    port_str = os.getenv("MCP_PORT", "8000")
    host_str = os.getenv("MCP_HOST", "0.0.0.0")
    try:
        port = int(port_str)
    except ValueError:
        print(
            f"Error: invalid MCP_PORT environment variable: {port_str!r}",
            file=sys.stderr,
        )
        sys.exit(1)

    forwarded_ips = os.getenv("FORWARDED_ALLOW_IPS", "*")

    uvicorn.run(
        app,
        host=host_str,
        port=port,
        proxy_headers=True,
        forwarded_allow_ips=forwarded_ips,
        log_level="info",
        log_config=UVICORN_LOGGING_CONFIG,
    )
