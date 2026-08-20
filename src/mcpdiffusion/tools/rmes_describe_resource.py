"""Tool: RMES_describe_resource -- thin registration layer."""
from __future__ import annotations

from fastmcp import FastMCP

from ..config.tool_metadata import RMES_DESCRIBE_RESOURCE
from ..core.logging import log_tool
from ..models.rmes import DescribeResourceInput, DescribeResourceOutput
from ..services.rmes import describe_resource


def register_rmes_describe_resource(mcp: FastMCP) -> None:
    @mcp.tool(
        name=RMES_DESCRIBE_RESOURCE["tool_name"],
        description=RMES_DESCRIBE_RESOURCE["tool_description"],
        meta=RMES_DESCRIBE_RESOURCE["tool_metadata"],
    )
    @log_tool
    async def describe_resource_tool(params: DescribeResourceInput) -> DescribeResourceOutput:
        return await describe_resource(params)
