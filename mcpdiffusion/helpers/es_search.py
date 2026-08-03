"""Shared Elasticsearch query-building helpers for the produit index.

Both `insee_search_documents` and `insee_search_conjoncture` run multi_match
searches against the same index shape. This module centralizes:

- `build_text_clauses` -- query + year + keyword clauses
- `apply_collection_filters` -- common must_not / theme / chiffre_clef logic
- `execute_search` -- run the assembled bool query and shape the response
- `DocumentHit` -- the whitelisted output record returned to models

The two search tools differ in:
- Which collection they restrict to (publications vs Informations rapides).
- Whether year_of_reference is added as a hard filter (both, now -- see note
  below).

Design note on `year_of_reference`
----------------------------------
Historically the two tools disagreed: one used year as a *hard filter*, the
other as a *soft should-boost*. That made identical queries return different
document sets depending on which tool was called. Both tools now apply the
year as a hard filter with `year_matches_title` -- a document titled
"Comptes nationaux 2020" is about 2020, period. The conjoncture use case
("show me the latest monthly release") is still served by leaving the year
unset; the search returns the newest match by score.
"""
from __future__ import annotations

from typing import Iterable, Optional

from elasticsearch import Elasticsearch
from elasticsearch.dsl import Q, Search
from pydantic import BaseModel, Field

from helpers.es import INDEX_PRODUITS, get_es_client
from tools.env import KEYS_THEME_NIV1, DICT_GEO


class DocumentHit(BaseModel):
    """Whitelisted publication record returned by INSEE.fr search tools.

    Fields are chosen so a model can:
    - present the result to the user (titre, soustitre, chapo, anneediffusion),
    - chain into `get_insee_document` via `url`,
    - rank/filter by geography and theme.
    """
    id: str = Field(description="Elasticsearch document id.")
    score: float = Field(description="Relevance score from Elasticsearch.")
    titre: Optional[str] = None
    soustitre: Optional[str] = None
    chapo: Optional[str] = None
    anneediffusion: Optional[str] = Field(
        default=None, description="Publication year as indexed."
    )
    zone: Optional[str] = Field(
        default=None, description="Geographic zone (e.g. 'France', 'Bretagne')."
    )
    theme: Optional[str] = None
    collection_libelle: Optional[str] = Field(
        default=None,
        description="Collection the publication belongs to "
                    "(e.g. 'Insee Premiere', 'Informations rapides').",
    )
    idproduit: Optional[str] = Field(
        default=None,
        description="INSEE product identifier (often equal to the ES id).",
    )
    url: str = Field(
        description="Relative URL ready to feed into `get_insee_document`."
    )


def _coerce_hit_value(value) -> Optional[str]:
    """ES can return lists or nested dicts for some fields; normalize to str|None."""
    if value is None:
        return None
    if isinstance(value, list):
        return ", ".join(str(v) for v in value) if value else None
    return str(value)


def build_text_clauses(
    query: Optional[str],
    year_of_reference: Optional[int],
    keywords: Iterable[str] = (),
) -> tuple[list, list, list, list]:
    """Return (must, filter, should, must_not) clause lists.

    - `query` drives the main multi_match (fuzzy) + a phrase-match should on titre.
    - `year_of_reference` is applied as a *hard filter* on title/subtitle/chapo.
      Rationale: a document titled "Bilan 2020" *is* about 2020; soft boosting
      was inconsistent across tools and led to same-query-different-results bugs.
    - `keywords` are optional extras that add should-clauses with a boost.
    """
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
        # Hard filter (see module docstring). Matches the year appearing in
        # title, subtitle or chapo. Documents without the year in any of
        # these fields are excluded -- this is the intended strictness.
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
    """Apply INSEE-specific filters to the running clause lists.

    Returns the updated (filters, should) pair. `must_not_rapides` and
    `must_only_rapides` are mutually exclusive callers: one restricts to
    publications (documents), the other to rapid releases (conjoncture).
    """
    should: list = []

    # Collection gating -- one or the other, never both.
    if must_only_rapides:
        filters.append(Q("term", collection_libelle="Informations rapides"))
    elif must_not_rapides:
        # Excludes rapid releases from the general publications search.
        # They have their own dedicated tool (search_insee_conjoncture).
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


def execute_search(
    *,
    must: list,
    filters: list,
    should: list,
    must_not: list,
    number_of_results: int,
    client: Optional[Elasticsearch] = None,
) -> list[DocumentHit]:
    """Run the assembled bool query and return whitelisted DocumentHit records."""
    client = client or get_es_client()

    s = Search(using=client, index=INDEX_PRODUITS).query(
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
    s = s[: max(1, number_of_results)]
    res = s.execute()

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
