"""Tool: get_melodi_observations -- thin registration layer."""
from __future__ import annotations

from fastmcp import Context, FastMCP

from ..config.tool_metadata import GET_DATASET
from ..infra.http import get_melodi_http_client
from ..models.melodi import GetMelodiObservationsInput, GetMelodiObservationsOutput
from ..services.melodi import get_melodi_observations


def register_get_melodi_observations(mcp: FastMCP) -> None:
    @mcp.tool(
        # Fixme: 'GET_DATASET' as variable name is too broad, thus misleading
        name=GET_DATASET["tool_name"],
        description=GET_DATASET["tool_description"],
        meta=GET_DATASET["tool_metadata"],
    )
    async def get_melodi_observations_tool(
        params: GetMelodiObservationsInput,
        ctx: Context,
    ) -> GetMelodiObservationsOutput:
        return await get_melodi_observations(params, http_client=get_melodi_http_client(ctx))
