"""HTTP client accessors from the FastMCP lifespan context."""

from fastmcp import Context
from httpx import AsyncClient


def get_insee_http_client(ctx: Context) -> AsyncClient:
    return ctx.lifespan_context["insee_http_client"]


def get_melodi_http_client(ctx: Context) -> AsyncClient:
    return ctx.lifespan_context["melodi_http_client"]
