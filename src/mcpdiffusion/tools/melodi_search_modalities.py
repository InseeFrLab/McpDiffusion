"""Tool: search_melodi_modalities -- thin registration layer."""
from __future__ import annotations

from fastmcp import Context, FastMCP

from ..config.tool_metadata import SEARCH_MODALITIES
from ..core.logging import log_tool
from ..infra.elasticsearch import get_client_es
from ..models.melodi import SearchMelodiModalitiesInput, SearchMelodiModalitiesOutput
from ..services.melodi import search_melodi_modalities


def register_search_melodi_modalities(mcp: FastMCP) -> None:
    @mcp.tool(
        name=SEARCH_MODALITIES["tool_name"],
        description=SEARCH_MODALITIES["tool_description"],
        meta=SEARCH_MODALITIES["tool_metadata"],
    )
    @log_tool
    async def search_melodi_modalities_tool(
        params: SearchMelodiModalitiesInput,
        ctx: Context,
    ) -> SearchMelodiModalitiesOutput:
        return await search_melodi_modalities(params, es=get_client_es(ctx))
