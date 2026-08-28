"""Elasticsearch client accessor from FastMCP lifespan context."""
# Fixme: this annotation seems unnecessary
from __future__ import annotations

from fastmcp import Context


def get_client_es(ctx: Context):
    return ctx.lifespan_context["es_client"]
