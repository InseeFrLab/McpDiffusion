"""Tool: search_melodi_datasets -- thin registration layer."""

from __future__ import annotations

from fastmcp import Context, FastMCP

from ..infra.elasticsearch import get_elasticsearch_client
from ..models.melodi import (
    DatasetQuery,
    DatasetsOutput,
    EndYear,
    NumberOfDatasets,
    StartYear,
)
from ..services.melodi import search_melodi_datasets_service


def register_search_melodi_datasets(mcp: FastMCP, *, index: str) -> None:
    @mcp.tool
    async def search_melodi_datasets(
        ctx: Context,
        query: DatasetQuery,
        start_year: StartYear = 1900,
        end_year: EndYear = 2100,
        number_of_datasets: NumberOfDatasets = 5,
    ) -> DatasetsOutput:
        """Search the INSEE Melodi dataset catalogue by French-language natural language query. Each
        dataset has a unique `dataset_id`; the tool maps the query to internal metadata to return the
        most relevant matches.

        Matching is lexical, so make the query explicit and rich in French synonyms, e.g.
        `"indice des prix a la consommation"`, `"deces par departement"`, `"prenoms des nouveau-nes"`.
        """
        return await search_melodi_datasets_service(
            query=query,
            start_year=start_year,
            end_year=end_year,
            number_of_datasets=number_of_datasets,
            es=get_elasticsearch_client(ctx),
            index=index,
        )
