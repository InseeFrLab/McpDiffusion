"""Tool: search_melodi_modalities -- thin registration layer."""

from __future__ import annotations

from fastmcp import Context, FastMCP

from ..config.tool_metadata import SEARCH_MODALITIES
from ..infra.elasticsearch import get_elasticsearch_client
from ..models.melodi import SearchMelodiModalitiesInput, SearchMelodiModalitiesOutput
from ..services.melodi import search_melodi_modalities


def register_search_melodi_modalities(mcp: FastMCP, *, index: str) -> None:
    @mcp.tool(
        name=SEARCH_MODALITIES["tool_name"],
        description=SEARCH_MODALITIES["tool_description"],
        meta=SEARCH_MODALITIES["tool_metadata"],
    )
    async def search_melodi_modalities_tool(
        params: SearchMelodiModalitiesInput,
        ctx: Context,
    ) -> SearchMelodiModalitiesOutput:
        return await search_melodi_modalities(
            params,
            es=get_elasticsearch_client(ctx),
            index=index,
        )
