"""Tool: RMES_list_graphs -- thin registration layer."""
from __future__ import annotations

from fastmcp import FastMCP

from ..config.tool_metadata import RMES_LIST_GRAPHS
from ..core.logging import log_tool
from ..models.rmes import ListGraphsInput, ListGraphsOutput
from ..services.rmes import list_graphs


def register_rmes_list_graphs(mcp: FastMCP) -> None:
    @mcp.tool(
        name=RMES_LIST_GRAPHS["tool_name"],
        description=RMES_LIST_GRAPHS["tool_description"],
        meta=RMES_LIST_GRAPHS["tool_metadata"],
    )
    @log_tool
    async def list_graphs_tool(params: ListGraphsInput) -> ListGraphsOutput:
        return await list_graphs(params)
