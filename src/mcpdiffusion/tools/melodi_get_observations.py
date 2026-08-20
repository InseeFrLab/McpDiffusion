"""Tool: get_melodi_observations -- thin registration layer."""
from __future__ import annotations

from fastmcp import FastMCP

from ..config.tool_metadata import GET_DATASET
from ..core.logging import log_tool
from ..models.melodi import GetMelodiObservationsInput, GetMelodiObservationsOutput
from ..services.melodi import get_melodi_observations


def register_get_melodi_observations(mcp: FastMCP) -> None:
    @mcp.tool(
        name=GET_DATASET["tool_name"],
        description=GET_DATASET["tool_description"],
        meta=GET_DATASET["tool_metadata"],
    )
    @log_tool
    async def get_melodi_observations_tool(
        params: GetMelodiObservationsInput,
    ) -> GetMelodiObservationsOutput:
        return await get_melodi_observations(params)
