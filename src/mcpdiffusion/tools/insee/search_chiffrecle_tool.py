"""Tool: search_insee_chiffrecle."""

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
    YearOfReference,
)
from ...services.insee.index_service import InseeIndexService


async def search_insee_chiffrecle(
    query: Query,
    year_of_reference: YearOfReference = None,
    geo_level: GeoLevel = GeoLevelChoice.FRANCE,
    geo_keyword: GeoKeyword = None,
    number_of_results: NumberOfResults = DEFAULT_RESULT_COUNT,
    insee_index_service: InseeIndexService = Depends(get_insee_index_service),
) -> DocumentSearchOutput:
    """Recherche EXCLUSIVE dans les Chiffres-clefs INSEE : donnees synthetiques, comparaisons
    regionales/departementales et statistiques factuelles simples.

    Retourne directement les tableaux synthetiques prets a l'emploi.
    """
    hits = await insee_index_service.search_chiffrecle(
        query=query,
        year_of_reference=year_of_reference,
        geo_level=geo_level,
        geo_keyword=geo_keyword,
        number_of_results=number_of_results,
    )
    return DocumentSearchOutput(
        results=hits,
        count=len(hits),
    )
