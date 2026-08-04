"""Tool: RMES_list_graphs

List named graphs available in the INSEE RDF database (RMES), grouped
by category with counts and example URIs.
"""
from __future__ import annotations

from typing import Any, Optional

from fastmcp import FastMCP
from pydantic import BaseModel, Field

from helpers.logging import log_tool
from helpers.rmes import (
    CATEGORY_DEFS,
    GraphCategoryChoice,
    GraphRow,
    SparqlError,
    _CATEGORY_AUTRE,
    _CategoryRule,
    _CATEGORY_FIELD_DESCRIPTION,
    _categorize,
    _get_raw_graph_rows,
)
from tools.env import RMES_LIST_GRAPHS


# ---------------------------------------------------------------------------
# Schémas Pydantic -- RMES_list_graphs
# ---------------------------------------------------------------------------

class ListGraphsInput(BaseModel):
    contains: Optional[str] = Field(
        default=None,
        description=(
            "Filtre les graphes dont l'URI contient cette sous-chaîne (insensible à la "
            "casse), ex. 'naf' ou 'qualite/rapport'. Active automatiquement le détail "
            "complet (`graphs`) dans les catégories retenues."
        ),
        examples=["naf", "qualite/rapport", "geo"],
    )
    category: GraphCategoryChoice = Field(
        default=GraphCategoryChoice.ALL,
        description=_CATEGORY_FIELD_DESCRIPTION,
    )
    expand: bool = Field(
        default=False,
        description=(
            "Si True, inclut la liste complète des graphes (URI + nb de triplets) pour "
            "chaque catégorie retenue, au lieu de seulement quelques exemples. Se "
            "déclenche automatiquement si `contains` est fourni ou `category != ALL`."
        ),
    )


class CategoryBucket(BaseModel):
    category: str
    label: str
    description: str
    count: int
    total_triples: int
    examples: list[str]
    graphs: Optional[list[GraphRow]] = None


class ListGraphsOutput(BaseModel):
    total_graphs_matched: int
    categories: list[CategoryBucket]
    error: Optional[SparqlError] = None


def _build_category_summary(rows: list[dict[str, Any]]) -> list[CategoryBucket]:
    buckets: dict[str, CategoryBucket] = {}
    for row in rows:
        cat = _categorize(row["graph"])
        bucket = buckets.get(cat.key)
        if bucket is None:
            bucket = CategoryBucket(
                category=cat.key,
                label=cat.label,
                description=cat.description,
                count=0,
                total_triples=0,
                examples=[],
            )
            buckets[cat.key] = bucket
        bucket.count += 1
        bucket.total_triples += row["triples"]
        if len(bucket.examples) < 5:
            bucket.examples.append(row["graph"])

    ordered_keys = [c.key for c in CATEGORY_DEFS] + [_CATEGORY_AUTRE.key]
    return [buckets[k] for k in ordered_keys if k in buckets]


# ---------------------------------------------------------------------------
# Enregistrement du tool MCP
# ---------------------------------------------------------------------------

def register_rmes_list_graphs(mcp: FastMCP) -> None:

    @mcp.tool(
        name=RMES_LIST_GRAPHS["tool_name"],
        description=RMES_LIST_GRAPHS["tool_description"],
        meta=RMES_LIST_GRAPHS["tool_metadata"],
    )
    @log_tool
    async def list_graphs(params: ListGraphsInput) -> ListGraphsOutput:
        raw = await _get_raw_graph_rows()
        if "error" in raw:
            return ListGraphsOutput(
                total_graphs_matched=0,
                categories=[],
                error=SparqlError(**raw["error"]),
            )
        rows = raw["rows"]
        expand = params.expand

        if params.contains:
            needle = params.contains.lower()
            rows = [r for r in rows if needle in r["graph"].lower()]
            expand = True

        if params.category != GraphCategoryChoice.ALL:
            rows = [r for r in rows if _categorize(r["graph"]).key == params.category.value]
            expand = True

        summary = _build_category_summary(rows)

        if expand:
            rows_by_graph = {r["graph"]: r["triples"] for r in rows}
            for bucket in summary:
                bucket_rows = [
                    GraphRow(graph=g, triples=t)
                    for g, t in rows_by_graph.items()
                    if _categorize(g).key == bucket.category
                ]
                bucket_rows.sort(key=lambda r: r.triples, reverse=True)
                bucket.graphs = bucket_rows

        return ListGraphsOutput(total_graphs_matched=len(rows), categories=summary)
