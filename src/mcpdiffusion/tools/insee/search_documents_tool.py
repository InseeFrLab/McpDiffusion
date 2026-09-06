"""Tool: search_insee_documents."""

from __future__ import annotations

from fastmcp.dependencies import Depends

from ...dependencies import get_insee_index_service
from ...models.insee import (
    DEFAULT_RESULT_COUNT,
    DocumentSearchOutput,
    GeoKeyword,
    GeoLevel,
    GeoLevelChoice,
    NumberOfResults,
    Query,
    Theme,
    ThemeChoice,
    YearOfReference,
)
from ...services.insee.index_service import InseeIndexService


async def search_insee_documents(
    query: Query,
    theme: Theme = ThemeChoice.ALL,
    year_of_reference: YearOfReference = None,
    geo_level: GeoLevel = GeoLevelChoice.FRANCE,
    geo_keyword: GeoKeyword = None,
    number_of_results: NumberOfResults = DEFAULT_RESULT_COUNT,
    insee_index_service: InseeIndexService = Depends(get_insee_index_service),
) -> DocumentSearchOutput:
    """Search the INSEE catalogue of official statistical publications (Insee Premiere, Insee
    Analyses, Dossiers, References, Focus, ...). Returns structured publication records; pass the
    URL of a record to `get_insee_document` to fetch the full text.

    Write a rich natural-language query with synonyms, context, and the target year or geography
    when relevant. For 'essentiel sur...' publications prefer `search_insee_chiffrecle`.
    """
    hits = await insee_index_service.search_documents(
        query=query,
        theme=theme,
        year_of_reference=year_of_reference,
        geo_level=geo_level,
        geo_keyword=geo_keyword,
        number_of_results=number_of_results,
    )
    return DocumentSearchOutput(
        results=hits,
        count=len(hits),
    )
