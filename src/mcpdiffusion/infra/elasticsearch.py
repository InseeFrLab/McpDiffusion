"""Elasticsearch client accessor from the FastMCP lifespan context."""

from elasticsearch import AsyncElasticsearch
from fastmcp import Context


def get_elasticsearch_client(ctx: Context) -> AsyncElasticsearch:
    return ctx.lifespan_context["elasticsearch_client"]
