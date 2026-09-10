"""Tool: search_melodi_modalities."""

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

    WHEN TO USE
    - You have a `dataset_id` (from `search_melodi_datasets`) and want to find the exact modality code for a
      concept like `cote de boeuf`, `Ile-de-France`, or `female Maria`.

    WHEN NOT TO USE
    - You don't yet know the dataset. Run `search_melodi_datasets` first.
    """
    results = await melodi_index_service.search_columns(
        dataset_id=dataset_id,
        column_ids=column_ids,
        query=query,
        number_of_modalities=number_of_modalities,
    )
    return ModalitiesOutput(results=results)
