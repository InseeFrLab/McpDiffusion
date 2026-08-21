"""Business logic for INSEE.fr Elasticsearch search tools.

Centralizes query building, collection filtering, and search execution
for search_insee_documents, search_insee_conjoncture, and search_insee_chiffrecle.
"""
from __future__ import annotations

from typing import Iterable, Optional

from elasticsearch import Elasticsearch
from elasticsearch.dsl import Q, Search

from ..config.settings import Settings, get_settings
from ..data.geography import DICT_GEO
from ..data.themes import KEYS_THEME_NIV1
from ..models.insee import DocumentHit


def _coerce_hit_value(value) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, list):
        return ", ".join(str(v) for v in value) if value else None
    return str(value)


# Build query 

def build_text_clauses(
    query: Optional[str],
    year_of_reference: Optional[int],
    keywords: Iterable[str] = (),
) -> tuple[list, list, list, list]:
    """Return (must, filter, should, must_not) clause lists."""
    must: list = []
    filters: list = []
    should: list = []
    must_not: list = []

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

    return must, filters, should, must_not


def apply_collection_filters(
    filters: list,
    *,
    must_not_rapides: bool,
    must_only_rapides: bool,
    chiffre_clef: bool = False,
    theme: Optional[str] = None,
    geo_niveau: Optional[str] = None,
    geo_keyword: Optional[str] = None,
) -> tuple[list, list]:
    """Apply INSEE-specific filters. Returns updated (filters, should)."""
    should: list = []

    if must_only_rapides:
        filters.append(Q("term", collection_libelle="Informations rapides"))
    elif must_not_rapides:
        filters.append(
            Q("bool", must_not=[Q("term", collection_libelle="Informations rapides")])
        )

    if theme and theme != "ALL":
        id_theme = KEYS_THEME_NIV1.get(theme)
        if id_theme is not None:
            filters.append(Q("term", idthemeparent=id_theme))

    if chiffre_clef:
        filters.append(Q("term", categorie_libelle="Chiffres-clés"))

    if geo_niveau:
        key_geo = DICT_GEO.get(geo_niveau)
        if key_geo:
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

def execute_search(
    *,
    must: list,
    filters: list,
    should: list,
    must_not: list,
    number_of_results: int,
    es: Elasticsearch,
    settings: Settings | None = None,
) -> list[DocumentHit]:
    """Run the assembled bool query and return whitelisted DocumentHit records."""
    s = settings or get_settings()
    search = Search(using=es, index=s.es_index_produits).query(
        Q(
            "function_score",
            query=Q(
                "bool",
                must=must,
                filter=filters,
                should=should,
                must_not=must_not,
                minimum_should_match=1 if should else 0,
            ),
            boost_mode="sum",
        )
    )
    search = search[: max(1, number_of_results)]
    res = search.execute()

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
