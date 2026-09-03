"""Tool: RMES_list_graphs -- thin registration layer."""
from __future__ import annotations

from fastmcp import Context, FastMCP

from ..config.tool_metadata import RMES_LIST_GRAPHS
from ..infra.sparql import get_sparql_http_client
from ..models.rmes import ListGraphsInput, ListGraphsOutput
from ..services.rmes import list_graphs


def register_rmes_list_graphs(mcp: FastMCP, *, endpoint: str) -> None:
    @mcp.tool(
        name=RMES_LIST_GRAPHS["tool_name"],
        description=RMES_LIST_GRAPHS["tool_description"],
        meta=RMES_LIST_GRAPHS["tool_metadata"],
    )
    async def list_graphs_tool(params: ListGraphsInput, ctx: Context) -> ListGraphsOutput:
        return await list_graphs(
            params,
            sparql_client=get_sparql_http_client(ctx),
            endpoint=endpoint,
        )
