"""Tool: RMES_describe_resource -- thin registration layer."""
from __future__ import annotations

from fastmcp import Context, FastMCP

from ..config.tool_metadata import RMES_DESCRIBE_RESOURCE
from ..infra.sparql import get_sparql_http_client
from ..models.rmes import DescribeResourceInput, DescribeResourceOutput
from ..services.rmes import describe_resource


def register_rmes_describe_resource(mcp: FastMCP, *, endpoint: str) -> None:
    @mcp.tool(
        name=RMES_DESCRIBE_RESOURCE["tool_name"],
        description=RMES_DESCRIBE_RESOURCE["tool_description"],
        meta=RMES_DESCRIBE_RESOURCE["tool_metadata"],
    )
    async def describe_resource_tool(params: DescribeResourceInput, ctx: Context) -> DescribeResourceOutput:
        return await describe_resource(
            params,
            sparql_client=get_sparql_http_client(ctx),
            endpoint=endpoint,
        )
