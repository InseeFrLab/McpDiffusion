"""Tool: search_melodi_datasets."""

from fastmcp.dependencies import Depends

from ...dependencies.melodi import get_melodi_index_service
from ...models.melodi import (
    DatasetQuery,
    DatasetsOutput,
    EndYear,
    NumberOfDatasets,
    StartYear,
)
from ...services.melodi.index_service import MelodiIndexService


async def search_melodi_datasets(
    query: DatasetQuery,
    start_year: StartYear = 1900,
    end_year: EndYear = 2100,
    number_of_datasets: NumberOfDatasets = 5,
    melodi_index_service: MelodiIndexService = Depends(get_melodi_index_service),
) -> DatasetsOutput:
    """Search the INSEE Melodi dataset catalogue by French-language natural language query. Each
    dataset has a unique `dataset_id`; the tool maps the query to internal metadata to return the
    most relevant matches.

    Matching is lexical, so make the query explicit and rich in French synonyms, e.g.
    `"indice des prix a la consommation"`, `"deces par departement"`, `"prenoms des nouveau-nes"`.

    WORKFLOW (chain these three, in order)
    1. `search_melodi_datasets` -> dataset_id + column ids
    2. `search_melodi_modalities` -> exact modality codes for filtering
    3. `get_melodi_observations` -> final observations

    WHEN TO USE
    - The user asks for a specific statistic (price of a product, mortality by region, frequency of a name, etc.)
      and you need to locate the right dataset before fetching rows.

    WHEN NOT TO USE
    - Generic, up-to-date indicator questions (use `get_insee_homepage`).
    - Full-text analysis of a published report (use `search_insee_documents`).
    - Definition/ontology lookups (use `run_rmes_sparql`).
    """
    results = await melodi_index_service.search_datasets(
        query=query,
        start_year=start_year,
        end_year=end_year,
        number_of_datasets=number_of_datasets,
    )
    return DatasetsOutput(results=results)
