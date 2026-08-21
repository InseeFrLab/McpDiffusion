"""SPARQL client accessor from FastMCP lifespan context."""
from __future__ import annotations

from fastmcp import Context


def get_sparql_client(ctx: Context):
    return ctx.lifespan_context["sparql_client"]
