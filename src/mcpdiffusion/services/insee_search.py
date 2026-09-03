"""Business logic for INSEE.fr Elasticsearch search tools.

Centralizes query building, collection filtering, and search execution
for search_insee_documents, search_insee_conjoncture, and search_insee_chiffrecle.
"""
from __future__ import annotations

from collections.abc import Iterable

from elasticsearch import AsyncElasticsearch
from elasticsearch.dsl import AsyncSearch, Q

from ..data.geography import DICT_GEO
from ..data.themes import KEYS_THEME_NIV1
from ..models.insee import DocumentHit

QueryClauses = tuple[list, list, list]


def _coerce_hit_value(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, list):
        return ", ".join(str(v) for v in value) if value else None
    return str(value)


# Build query 
def build_text_clauses(
    query: str | None,
    year_of_reference: int | None,
    keywords: Iterable[str] = (),
) -> QueryClauses:
    """Return the (must, filter, should) clause lists for a text query."""
    must: list = []
    filters: list = []
    should: list = []

    if query:
        must.append(
            Q(
                "multi_match",
                query=query,
                fields=[
                    "titre^5",
                    "titre.ngram^3",
                    "soustitre^2",
                    "zone^5",
                    "chapo",
                    "theme",
                ],
                fuzziness="AUTO",
            )
        )
        should.append(
            Q("match_phrase", titre={"query": query, "boost": 1})
        )

    if year_of_reference:
        filters.append(
            Q(
                "multi_match",
                query=str(year_of_reference),
                fields=["titre^10", "soustitre^5", "chapo^5"],
            )
        )

    for kw in keywords or ():
        should.append(
            Q(
                "multi_match",
                query=kw,
                fields=["titre^3", "soustitre^2", "chapo", "theme"],
                fuzziness="AUTO",
                boost=2,
            )
        )

    return must, filters, should


def apply_collection_filters(
    filters: list,
    *,
    must_not_rapides: bool,
    must_only_rapides: bool,
    chiffre_clef: bool = False,
    theme: str | None = None,
    geo_niveau: str | None = None,
    geo_keyword: str | None = None,
) -> tuple[list, list]:
    """Return new (filters, should) lists. The caller's `filters` is left untouched."""
    filters = list(filters)
    should: list = []

    if must_only_rapides:
        filters.append(Q("term", collection_libelle="Informations rapides"))
    elif must_not_rapides:
        filters.append(
            Q("bool", must_not=[Q("term", collection_libelle="Informations rapides")])
        )

    # Fixme: the 1st check seems useless
    if theme and theme != "ALL":
        # Business rule: an unrecognised theme drops the filter silently, so the search returns more
        # than the caller asked for. Reject the value, or accept it and say so in the response?
        id_theme = KEYS_THEME_NIV1.get(theme)
        if id_theme is not None:
            filters.append(Q("term", idthemeparent=id_theme))

    if chiffre_clef:
        filters.append(Q("term", categorie_libelle="Chiffres-clés"))

    if geo_niveau:
        key_geo = DICT_GEO.get(geo_niveau)
        if key_geo:
            # Business rule: same as the theme filter above — an unrecognised geo_niveau is dropped
            # silently and broadens the search.
            filters.append(Q("term", geo_niveau=key_geo))

    if geo_keyword and geo_keyword.lower() != "all":
        should.append(
            Q(
                "multi_match",
                query=geo_keyword,
                fields=["titre^5", "titre.ngram^3", "soustitre^2", "zone^10"],
                fuzziness="AUTO",
            )
        )
        should.append(
            Q("match_phrase", zone={"query": geo_keyword, "boost": 5})
        )

    return filters, should

# Execute search with built query 

async def execute_search(
    *,
    must: list,
    filters: list,
    should: list,
    minimum_should_match: int,
    number_of_results: int,
    es: AsyncElasticsearch,
    index: str,
) -> list[DocumentHit]:
    """Run the assembled bool query and return whitelisted DocumentHit records."""
    search = AsyncSearch(using=es, index=index).query(
        Q(
            "function_score",
            query=Q(
                "bool",
                must=must,
                filter=filters,
                should=should,
                # `should` mixes pure score boosts with the geo clauses, which the caller wants
                # required when present. Only the caller knows which it passed, so it decides.
                # Business rule: a supplied `geo_keyword` is currently *required* to match, not just
                # boosted, so it silently narrows results. Confirm this is intended.
                minimum_should_match=minimum_should_match,
            ),
            boost_mode="sum",
        )
    )
    search = search[: max(1, number_of_results)]
    res = await search.execute()

    hits: list[DocumentHit] = []
    for hit in res:
        d = hit.to_dict()
        doc_id = str(hit.meta.id)
        hits.append(
            DocumentHit(
                id=doc_id,
                score=float(hit.meta.score or 0.0),
                titre=_coerce_hit_value(d.get("titre")),
                soustitre=_coerce_hit_value(d.get("soustitre")),
                chapo=_coerce_hit_value(d.get("chapo")),
                anneediffusion=_coerce_hit_value(d.get("anneediffusion")),
                zone=_coerce_hit_value(d.get("zone")),
                theme=_coerce_hit_value(d.get("theme")),
                collection_libelle=_coerce_hit_value(d.get("collection_libelle")),
                idproduit=_coerce_hit_value(d.get("idproduit")),
                url=f"/fr/statistiques/{doc_id}",
            )
        )
    return hits
