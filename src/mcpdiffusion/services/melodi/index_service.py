"""Melodi's Elasticsearch access: query construction, execution and parsing.

Elasticsearch vocabulary stops here. Tools never see a `Hit`, a `_source` or an `inner_hits`
envelope, so a change in the index shape is contained to this file.
"""

from __future__ import annotations

from elasticsearch import AsyncElasticsearch
from elasticsearch.dsl import AsyncSearch, Q
from elasticsearch.dsl.query import Query
from elasticsearch.dsl.response import Hit
from elasticsearch.dsl.utils import AttrList

from ...models.melodi import (
    ColumnResult,
    DatasetDescription,
    DatasetSearchResult,
    Modality,
)
from ..elasticsearch_failures import elasticsearch_failures_as_tool_errors

# The column query asks for a fixed page of columns and narrows within them via inner_hits.
COLUMN_SEARCH_SIZE = 20


# ----------------------------------------------------------------------------------------------------------------------
# Query builders -------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------

# Pure: no client, no index, no I/O. A client-less `AsyncSearch` is valid on its own, so the body
# these produce is assertable without an Elasticsearch instance. The service binds `.using()` and
# `.index()` before executing.


def build_dataset_search(
    query: str,
    start_year: int,
    end_year: int,
    number_of_datasets: int,
) -> AsyncSearch:
    """Rank datasets on title, abstract, description and variable text, title weighing most.

    A year of 0 means "unbounded", so it contributes no range filter.
    """
    filters: list[Query] = []
    if start_year:
        filters.append(Q("range", **{"metadata.temporal.endPeriod": {"gte": f"{start_year}-01-01"}}))
    if end_year:
        filters.append(Q("range", **{"metadata.temporal.startPeriod": {"lte": f"{end_year}-12-31"}}))

    def match_nested_content(path: str, boost: int) -> Query:
        return Q(
            "nested",
            path=path,
            query=Q("match", **{f"{path}.content": {"query": query, "boost": boost}}),
        )

    return AsyncSearch().query(
        Q(
            "bool",
            should=[
                match_nested_content("metadata.title", 10),
                match_nested_content("metadata.abstract", 6),
                match_nested_content("metadata.description", 3),
                Q("match", variables_text={"query": query, "boost": 5}),
            ],
            filter=filters,
        )
    )[:number_of_datasets]


def build_column_search(
    dataset_id: str,
    column_ids: list[str],
    query: str,
    number_of_modalities: int,
) -> AsyncSearch:
    """Find the dataset's columns whose text or modality labels match, keeping the best modalities.

    `number_of_modalities` caps the inner hits, not the columns: the page of columns is fixed.
    `inner_hits` is what makes Elasticsearch report *which* nested modalities matched, and with
    what score -- a plain match would only say the column matched. The typed `InnerHits` object
    serialises `sort` to a string in elasticsearch 9.5.0, so the clause stays a plain dict.
    """
    filters: list[Query] = [Q("term", dataset_id=dataset_id)]
    if column_ids:
        filters.append(Q("terms", code=column_ids))

    return AsyncSearch().query(
        Q(
            "bool",
            filter=filters,
            should=[
                Q("match", text={"query": query, "boost": 2}),
                Q(
                    "nested",
                    path="modalities",
                    score_mode="max",
                    query=Q(
                        "multi_match",
                        query=query,
                        fields=[
                            "modalities.code^5",
                            "modalities.label.en^3",
                            "modalities.label.fr^3",
                        ],
                        fuzziness="AUTO",
                    ),
                    inner_hits={
                        "size": number_of_modalities,
                        "sort": [
                            {"_score": "desc"},
                        ],
                    },
                ),
            ],
        )
    )[:COLUMN_SEARCH_SIZE]


# ----------------------------------------------------------------------------------------------------------------------
# Hit helpers ----------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------


def parse_first_description(dataset_hit: Hit) -> DatasetDescription:
    """Return a dataset's first description, or an empty French one when it has none.

    Descriptions arrive as an array, as a single object, or not at all. The DSL wraps a JSON array
    in `AttrList`, which is not a `list`, so both types have to be named or every description
    parses as empty.
    """
    metadata = getattr(dataset_hit, "metadata", None)
    description = getattr(metadata, "description", None) if metadata is not None else None
    if isinstance(description, list | AttrList):
        description = description[0] if len(description) else None
    if description is None:
        return DatasetDescription(content="", lang="fr")
    return DatasetDescription(
        content=getattr(description, "content", ""),
        lang=getattr(description, "lang", "fr"),
    )


def parse_modality(modality_hit: Hit) -> Modality:
    """Map one matched nested modality, with the score that ranked it."""
    label = getattr(modality_hit, "label", None)
    return Modality(
        code=getattr(modality_hit, "code", ""),
        label_fr=getattr(label, "fr", ""),
        label_en=getattr(label, "en", ""),
        # A non-scoring query reports a null score, which is not a float.
        score=getattr(modality_hit.meta, "score", 0.0) or 0.0,
    )


# ----------------------------------------------------------------------------------------------------------------------
# Service --------------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------


class MelodiIndexService:
    """Searches the two Melodi Elasticsearch indices.

    Holds the client and the index names, so nothing above has to carry an index around.
    """

    def __init__(
        self,
        elasticsearch_client: AsyncElasticsearch,
        datasets_index: str,
        columns_index: str,
    ) -> None:
        self._elasticsearch_client = elasticsearch_client
        self._datasets_index = datasets_index
        self._columns_index = columns_index

    async def search_datasets(
        self,
        query: str,
        start_year: int,
        end_year: int,
        number_of_datasets: int,
    ) -> list[DatasetSearchResult]:
        """Return the datasets matching the query, most relevant first."""
        search = (
            build_dataset_search(
                query=query,
                start_year=start_year,
                end_year=end_year,
                number_of_datasets=number_of_datasets,
            )
            .using(self._elasticsearch_client)
            .index(self._datasets_index)
        )
        async with elasticsearch_failures_as_tool_errors("Melodi datasets"):
            response = await search.execute()

        results: list[DatasetSearchResult] = []
        for dataset_hit in response:
            results.append(
                DatasetSearchResult(
                    dataset_id=dataset_hit.meta.id,
                    dataset_columns=getattr(dataset_hit, "columns", ""),
                    dataset_description=parse_first_description(dataset_hit),
                    dataset_score=getattr(dataset_hit.meta, "score", 0.0) or 0.0,
                )
            )
        return results

    async def search_columns(
        self,
        dataset_id: str,
        column_ids: list[str],
        query: str,
        number_of_modalities: int,
    ) -> list[ColumnResult]:
        """Return the dataset's matching columns, each with its top-scoring modalities."""
        search = (
            build_column_search(
                dataset_id=dataset_id,
                column_ids=column_ids,
                query=query,
                number_of_modalities=number_of_modalities,
            )
            .using(self._elasticsearch_client)
            .index(self._columns_index)
        )
        async with elasticsearch_failures_as_tool_errors("Melodi columns"):
            response = await search.execute()

        results: list[ColumnResult] = []
        for column_hit in response:
            inner_hits = getattr(column_hit.meta, "inner_hits", None)
            modality_hits = getattr(inner_hits, "modalities", []) if inner_hits is not None else []
            results.append(
                ColumnResult(
                    column_code=getattr(column_hit, "code", ""),
                    column_metadata=getattr(column_hit, "text", ""),
                    matching_modalities=[parse_modality(modality_hit) for modality_hit in modality_hits],
                )
            )
        return results
