"""Tool: search_melodi_datasets -- thin registration layer."""
from __future__ import annotations

from fastmcp import Context, FastMCP

from ..config.tool_metadata import SEARCH_DATASET
from ..infra.elasticsearch import get_elasticsearch_client
from ..models.melodi import SearchMelodiDatasetsInput, SearchMelodiDatasetsOutput
from ..services.melodi import search_melodi_datasets


def register_search_melodi_datasets(mcp: FastMCP, *, index: str) -> None:
    @mcp.tool(
        name=SEARCH_DATASET["tool_name"],
        description=SEARCH_DATASET["tool_description"],
        meta=SEARCH_DATASET["tool_metadata"],
    )
    async def search_melodi_datasets_tool(
        params: SearchMelodiDatasetsInput,
        ctx: Context,
    ) -> SearchMelodiDatasetsOutput:
        return await search_melodi_datasets(
            params,
            es=get_elasticsearch_client(ctx),
            index=index,
        )
