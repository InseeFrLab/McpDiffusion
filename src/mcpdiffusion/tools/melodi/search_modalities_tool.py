"""Tool: search_melodi_modalities."""

from __future__ import annotations

from fastmcp.dependencies import Depends

from ...dependencies.melodi import get_melodi_index_service
from ...models.melodi import (
    ColumnIds,
    DatasetId,
    ModalitiesOutput,
    ModalityQuery,
    NumberOfModalities,
)
from ...services.melodi.index_service import MelodiIndexService


async def search_melodi_modalities(
    dataset_id: DatasetId,
    column_ids: ColumnIds,
    query: ModalityQuery,
    number_of_modalities: NumberOfModalities = 10,
    melodi_index_service: MelodiIndexService = Depends(get_melodi_index_service),
) -> ModalitiesOutput:
    """Given a Melodi dataset and one or more column identifiers, rank the most relevant modalities
    (codes/labels) for a free-text French query. The result is what you need to filter rows in
    `get_melodi_observations`.

    Each matching column carries its `code`, its metadata text and the top-scoring
    `matching_modalities`. An empty list means nothing matched.
    """
    results = await melodi_index_service.search_columns(
        dataset_id=dataset_id,
        column_ids=column_ids,
        query=query,
        number_of_modalities=number_of_modalities,
    )
    return ModalitiesOutput(results=results)
