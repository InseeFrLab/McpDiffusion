"""HTTP client accessor from FastMCP lifespan context."""
from __future__ import annotations

from fastmcp import Context


def get_http_client(ctx: Context):
    return ctx.lifespan_context["http_client"]
