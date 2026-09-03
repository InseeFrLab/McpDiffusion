"""SPARQL client accessor from the FastMCP lifespan context."""

from fastmcp import Context
from httpx import AsyncClient


def get_sparql_http_client(ctx: Context) -> AsyncClient:
    return ctx.lifespan_context["sparql_http_client"]
