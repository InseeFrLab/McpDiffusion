"""Tool: RMES_describe_resource

Retrieve all known properties (predicate -> value) of an RDF resource
identified by its full URI, across all graphs or restricted to one.
"""
from __future__ import annotations

from typing import Any, Literal, Optional

from fastmcp import FastMCP
from pydantic import BaseModel, Field

from helpers.logging import log_tool
from helpers.rmes import (
    DEFAULT_TIMEOUT,
    MAX_ROW_LIMIT,
    SparqlError,
    _execute_sparql,
)
from tools.env import RMES_DESCRIBE_RESOURCE


# ---------------------------------------------------------------------------
# Schémas Pydantic -- RMES_describe_resource
# ---------------------------------------------------------------------------

class DescribeResourceInput(BaseModel):
    uri: str = Field(
        description="URI complète de la ressource RDF à décrire.",
        examples=["http://id.insee.fr/codes/naf2025/section/A"],
    )
    graph: str | None = Field(
        default=None,
        description=(
            "URI d'un graphe nommé pour restreindre la recherche. Sans cette valeur (None par défaut), "
            "la recherche se fait sur tous les graphes (plus lent)."
        ),
    )


class ResourceProperty(BaseModel):
    graph: str
    direction: Literal["outgoing", "incoming"]
    predicate: str
    value: str
    value_type: Optional[str] = None
    lang: Optional[str] = None


class DescribeResourceOutput(BaseModel):
    uri: str
    properties: list[ResourceProperty]
    count: int
    error: Optional[SparqlError] = None


def _parse_bindings_to_properties(bindings: list[dict[str, Any]]) -> list[ResourceProperty]:
    props: list[ResourceProperty] = []
    for b in bindings:
        props.append(
            ResourceProperty(
                graph=b["g"]["value"],
                direction=b["direction"]["value"],
                predicate=b["p"]["value"],
                value=b["o"]["value"],
                value_type=b["o"].get("type"),
                lang=b["o"].get("xml:lang"),
            )
        )
    return props


# ---------------------------------------------------------------------------
# Enregistrement du tool MCP
# ---------------------------------------------------------------------------

def register_rmes_describe_resource(mcp: FastMCP) -> None:

    @mcp.tool(
        name=RMES_DESCRIBE_RESOURCE["tool_name"],
        description=RMES_DESCRIBE_RESOURCE["tool_description"],
        meta=RMES_DESCRIBE_RESOURCE["tool_metadata"],
    )
    @log_tool
    async def describe_resource(params: DescribeResourceInput) -> DescribeResourceOutput:
        graph_clause = f"<{params.graph}>" if params.graph else "?g"
        graph_values = f"VALUES ?g {{ <{params.graph}> }}" if params.graph else ""
        query = f"""
        SELECT ?g ?direction ?p ?o WHERE {{
          {graph_values}
          {{
            GRAPH {graph_clause} {{ <{params.uri}> ?p ?o }}
            BIND("outgoing" AS ?direction)
          }} UNION {{
            GRAPH {graph_clause} {{ ?o ?p <{params.uri}> }}
            BIND("incoming" AS ?direction)
          }}
        }} LIMIT {MAX_ROW_LIMIT}
        """
        result = await _execute_sparql(query, timeout=DEFAULT_TIMEOUT, max_rows=MAX_ROW_LIMIT)

        if "error" in result:
            return DescribeResourceOutput(
                uri=params.uri, properties=[], count=0, error=SparqlError(**result["error"])
            )

        properties = _parse_bindings_to_properties(result["results"]["bindings"])
        return DescribeResourceOutput(uri=params.uri, properties=properties, count=len(properties))
