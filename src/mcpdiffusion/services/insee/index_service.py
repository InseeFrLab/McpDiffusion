"""INSEE's Elasticsearch access: query construction, execution and parsing.

Elasticsearch vocabulary stops here. Tools never see a `Hit` or a `_source` envelope, so a change
in the index shape is contained to this file.

The three searches share one index and one text-matching rule, and differ only in the collection
they keep and the filters they add. Each gets its own builder rather than one builder driven by
boolean flags, so no caller can ask for a combination that makes no sense.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from elasticsearch import AsyncElasticsearch
from elasticsearch.dsl import AsyncSearch, Q
from elasticsearch.dsl.query import Query
from elasticsearch.dsl.response import Response

from ...data.insee.geography import DICT_GEO
from ...data.insee.themes import DICT_THEME_CONJ, KEYS_THEME_NIV1
from ...errors.elasticsearch_tool_error_handler import elasticsearch_tool_error_handler
from ...models.insee import DocumentHit

RAPIDES_COLLECTION = "Informations rapides"
CHIFFRES_CLES_CATEGORY = "Chiffres-clés"


@dataclass(frozen=True)
class QueryClauses:
    """The clause lists of an Elasticsearch `bool` query, named rather than positional.

    A builder that contributes nothing to one of them leaves it empty; the search builders then
    concatenate the parts in the order Elasticsearch receives them.
    """

    must: list[Query] = field(default_factory=list)
    filter: list[Query] = field(default_factory=list)
    should: list[Query] = field(default_factory=list)


# ----------------------------------------------------------------------------------------------------------------------
# Shared clause builders -----------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------


def build_text_clauses(
    query: str | None,
    year_of_reference: int | None,
    keywords: Iterable[str] = (),
) -> QueryClauses:
    """Return the clauses matching a text query, optionally pinned to a publication year."""
    must: list[Query] = []
    filters: list[Query] = []
    should: list[Query] = []

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
        should.append(Q("match_phrase", titre={"query": query, "boost": 1}))

    if year_of_reference:
        filters.append(
            Q(
                "multi_match",
                query=str(year_of_reference),
                fields=["titre^10", "soustitre^5", "chapo^5"],
            )
        )

    for keyword in keywords or ():
        should.append(
            Q(
                "multi_match",
                query=keyword,
                fields=["titre^3", "soustitre^2", "chapo", "theme"],
                fuzziness="AUTO",
                boost=2,
            )
        )

    return QueryClauses(
        must=must,
        filter=filters,
        should=should,
    )


def build_geography_clauses(
    geo_level: str | None,
    geo_keyword: str | None,
) -> QueryClauses:
    """Return the clauses that narrow a search to a place. Contributes no `must`."""
    filters: list[Query] = []
    should: list[Query] = []

    if geo_level:
        key_geo = DICT_GEO.get(geo_level)
        if key_geo:
            # Business rule: an unrecognised geo_niveau is dropped silently and broadens the search.
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
        should.append(Q("match_phrase", zone={"query": geo_keyword, "boost": 5}))

    return QueryClauses(
        filter=filters,
        should=should,
    )


def assemble_search(
    clauses: QueryClauses,
    minimum_should_match: int,
    number_of_results: int,
) -> AsyncSearch:
    """Wrap the assembled clauses in the scoring query every INSEE search shares."""
    return AsyncSearch().query(
        Q(
            "function_score",
            query=Q(
                "bool",
                must=clauses.must,
                filter=clauses.filter,
                should=clauses.should,
                # `should` mixes pure score boosts with the geo clauses, which the caller wants
                # required when present. Only the caller knows which it passed, so it decides.
                # Business rule: a supplied `geo_keyword` is currently *required* to match, not just
                # boosted, so it silently narrows results. Confirm this is intended.
                minimum_should_match=minimum_should_match,
            ),
            boost_mode="sum",
        )
    )[: max(1, number_of_results)]


# ----------------------------------------------------------------------------------------------------------------------
# One builder per search -----------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------


def build_documents_search(
    query: str,
    theme: str | None,
    year_of_reference: int | None,
    geo_level: str | None,
    geo_keyword: str | None,
    number_of_results: int,
) -> AsyncSearch:
    """Search the whole catalogue except Informations rapides, which has its own tool."""
    text = build_text_clauses(
        query=query,
        year_of_reference=year_of_reference,
    )
    collection_filters = [Q("bool", must_not=[Q("term", collection_libelle=RAPIDES_COLLECTION)])]

    if theme != "ALL":
        # Business rule: an unrecognised theme drops the filter silently, so the search returns more
        # than the caller asked for. Reject the value, or accept it and say so in the response?
        id_theme = KEYS_THEME_NIV1.get(theme)
        if id_theme is not None:
            collection_filters.append(Q("term", idthemeparent=id_theme))

    geography = build_geography_clauses(
        geo_level=geo_level,
        geo_keyword=geo_keyword,
    )
    return assemble_search(
        clauses=QueryClauses(
            must=text.must,
            filter=text.filter + collection_filters + geography.filter,
            should=text.should + geography.should,
        ),
        minimum_should_match=1 if geography.should else 0,
        number_of_results=number_of_results,
    )


def build_conjoncture_search(
    query: str,
    theme_conjoncture: str | None,
    year_of_reference: int | None,
    number_of_results: int,
) -> AsyncSearch:
    """Search only Informations rapides, optionally narrowed to a conjoncture subtheme."""
    text = build_text_clauses(
        query=query,
        year_of_reference=year_of_reference,
    )
    collection_filters = [Q("term", collection_libelle=RAPIDES_COLLECTION)]

    if theme_conjoncture:
        subthemes = DICT_THEME_CONJ.get(theme_conjoncture)
        # Business rule: an unrecognised subtheme drops the filter silently and returns everything,
        # the same shape as the theme and geo_level filters.
        if subthemes:
            collection_filters.append(Q("terms", conjoncture_libelle=subthemes))

    # This search takes no geography, so nothing in `should` is ever required to match.
    return assemble_search(
        clauses=QueryClauses(
            must=text.must,
            filter=text.filter + collection_filters,
            should=text.should,
        ),
        minimum_should_match=0,
        number_of_results=number_of_results,
    )


def build_chiffrecle_search(
    query: str,
    year_of_reference: int | None,
    geo_level: str | None,
    geo_keyword: str | None,
    number_of_results: int,
) -> AsyncSearch:
    """Search only the key-figure documents, excluding Informations rapides."""
    text = build_text_clauses(
        query=query,
        year_of_reference=year_of_reference,
    )
    collection_filters = [
        Q("bool", must_not=[Q("term", collection_libelle=RAPIDES_COLLECTION)]),
        Q("term", categorie_libelle=CHIFFRES_CLES_CATEGORY),
    ]

    geography = build_geography_clauses(
        geo_level=geo_level,
        geo_keyword=geo_keyword,
    )
    return assemble_search(
        clauses=QueryClauses(
            must=text.must,
            filter=text.filter + collection_filters + geography.filter,
            should=text.should + geography.should,
        ),
        minimum_should_match=1 if geography.should else 0,
        number_of_results=number_of_results,
    )


# ----------------------------------------------------------------------------------------------------------------------
# Parsing --------------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------


def format_hit_field(value: object) -> str | None:
    """Render one indexed field as text, joining a multi-valued field into a readable list."""
    if value is None:
        return None
    if isinstance(value, list):
        return ", ".join(str(item) for item in value) if value else None
    return str(value)


def parse_document_hits(response: Response) -> list[DocumentHit]:
    """Map catalogue hits onto the records the tools return, keeping only whitelisted fields."""
    hits: list[DocumentHit] = []
    for hit in response:
        source = hit.to_dict()
        document_id = hit.meta.id
        hits.append(
            DocumentHit(
                id=document_id,
                # A non-scoring query reports a null score, which is not a float.
                score=hit.meta.score or 0.0,
                titre=format_hit_field(source.get("titre")),
                soustitre=format_hit_field(source.get("soustitre")),
                chapo=format_hit_field(source.get("chapo")),
                anneediffusion=format_hit_field(source.get("anneediffusion")),
                zone=format_hit_field(source.get("zone")),
                theme=format_hit_field(source.get("theme")),
                collection_libelle=format_hit_field(source.get("collection_libelle")),
                idproduit=format_hit_field(source.get("idproduit")),
                url=f"/fr/statistiques/{document_id}",
            )
        )
    return hits


# ----------------------------------------------------------------------------------------------------------------------
# Service --------------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------


class InseeIndexService:
    """Searches the insee.fr publication index.

    Holds the client and the index name, so nothing above has to carry an index around.
    """

    def __init__(
        self,
        elasticsearch_client: AsyncElasticsearch,
        publications_index: str,
    ) -> None:
        self._elasticsearch_client = elasticsearch_client
        self._publications_index = publications_index

    async def _run(
        self,
        search: AsyncSearch,
        backend_label: str,
    ) -> list[DocumentHit]:
        """Bind the search to the client and index, execute it, and map the hits."""
        bound = search.using(self._elasticsearch_client).index(self._publications_index)
        async with elasticsearch_tool_error_handler(backend_label):
            response = await bound.execute()
        return parse_document_hits(response)

    async def search_documents(
        self,
        query: str,
        theme: str | None,
        year_of_reference: int | None,
        geo_level: str | None,
        geo_keyword: str | None,
        number_of_results: int,
    ) -> list[DocumentHit]:
        """Return catalogue publications matching the query, most relevant first."""
        return await self._run(
            build_documents_search(
                query=query,
                theme=theme,
                year_of_reference=year_of_reference,
                geo_level=geo_level,
                geo_keyword=geo_keyword,
                number_of_results=number_of_results,
            ),
            "INSEE documents",
        )

    async def search_conjoncture(
        self,
        query: str,
        theme_conjoncture: str | None,
        year_of_reference: int | None,
        number_of_results: int,
    ) -> list[DocumentHit]:
        """Return Informations rapides matching the query, most relevant first."""
        return await self._run(
            build_conjoncture_search(
                query=query,
                theme_conjoncture=theme_conjoncture,
                year_of_reference=year_of_reference,
                number_of_results=number_of_results,
            ),
            "INSEE conjoncture",
        )

    async def search_chiffrecle(
        self,
        query: str,
        year_of_reference: int | None,
        geo_level: str | None,
        geo_keyword: str | None,
        number_of_results: int,
    ) -> list[DocumentHit]:
        """Return key-figure publications matching the query, most relevant first."""
        return await self._run(
            build_chiffrecle_search(
                query=query,
                year_of_reference=year_of_reference,
                geo_level=geo_level,
                geo_keyword=geo_keyword,
                number_of_results=number_of_results,
            ),
            "INSEE chiffres-cles",
        )
