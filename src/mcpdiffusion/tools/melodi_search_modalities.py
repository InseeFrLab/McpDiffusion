"""Tool: search_melodi_modalities -- thin registration layer."""

from __future__ import annotations

from fastmcp import Context, FastMCP

from ..infra.elasticsearch import get_elasticsearch_client
from ..models.melodi import (
    ColumnIds,
    DatasetId,
    ModalitiesOutput,
    ModalityQuery,
    NumberOfModalities,
)
from ..services.melodi import search_melodi_modalities_service


def register_search_melodi_modalities(mcp: FastMCP, *, index: str) -> None:
    @mcp.tool
    async def search_melodi_modalities(
        ctx: Context,
        dataset_id: DatasetId,
        column_ids: ColumnIds,
        query: ModalityQuery,
        number_of_modalities: NumberOfModalities = 10,
    ) -> ModalitiesOutput:
        """Given a Melodi dataset and one or more column identifiers, rank the most relevant modalities
        (codes/labels) for a free-text French query. The result is what you need to filter rows in
        `get_melodi_observations`.

        Each matching column carries its `code`, its metadata text and the top-scoring
        `matching_modalities`. An empty list means nothing matched.
        """
        return await search_melodi_modalities_service(
            dataset_id=dataset_id,
            column_ids=column_ids,
            query=query,
            number_of_modalities=number_of_modalities,
            es=get_elasticsearch_client(ctx),
            index=index,
        )
