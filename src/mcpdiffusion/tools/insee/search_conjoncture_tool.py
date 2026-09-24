"""Tool: search_insee_conjoncture."""

from fastmcp.dependencies import Depends

from ...dependencies.insee import get_insee_index_service
from ...models.insee import (
    DEFAULT_RESULT_COUNT,
    ConjonctureQuery,
    ConjonctureYearOfReference,
    DocumentSearchOutput,
    NumberOfResults,
    ThemeConjoncture,
)
from ...services.insee.index_service import InseeIndexService


async def search_insee_conjoncture(
    query: ConjonctureQuery,
    theme_conjoncture: ThemeConjoncture = None,
    year_of_reference: ConjonctureYearOfReference = None,
    number_of_results: NumberOfResults = DEFAULT_RESULT_COUNT,
    insee_index_service: InseeIndexService = Depends(get_insee_index_service),
) -> DocumentSearchOutput:
    """Search INSEE Rapid Releases (Informations rapides): short, recurring publications reporting
    the latest monthly/quarterly/annual results for major economic and social indicators (prices,
    employment, production, housing, wages, national accounts, ...).

    The search is lexical and rewards keyword breadth, so provide several synonyms and related
    notions.

    WHEN TO USE
    - The user asks for the *latest* monthly/quarterly release of a named indicator (e.g. last month's consumer
      confidence, last quarter's GDP estimate). Prefer the most recent edition.

    WHEN NOT TO USE
    - Generic up-to-date indicator on the homepage: `get_insee_homepage`.
    - Deep, peer-reviewed analysis: `search_insee_documents`.
    """
    hits = await insee_index_service.search_conjoncture(
        query=query,
        theme_conjoncture=theme_conjoncture,
        year_of_reference=year_of_reference,
        number_of_results=number_of_results,
    )
    return DocumentSearchOutput(
        results=hits,
        count=len(hits),
    )
