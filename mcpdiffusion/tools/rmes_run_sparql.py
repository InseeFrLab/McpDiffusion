"""Tool: RMES_run_sparql

Execute arbitrary SPARQL queries against the INSEE semantic graph (RMES).
Supports SELECT, ASK, CONSTRUCT, and DESCRIBE forms.
"""
from __future__ import annotations

from typing import Any, Literal, Optional

from fastmcp import FastMCP
from pydantic import BaseModel, Field

from helpers.logging import log_tool
from helpers.rmes import (
    DEFAULT_ROW_LIMIT,
    DEFAULT_TIMEOUT,
    KNOWN_VOCABULARIES_NOTE,
    MAX_ROW_LIMIT,
    MAX_TIMEOUT,
    SparqlError,
    SparqlErrorType,
    _execute_sparql,
)
from tools.env import RMES_RUN_SPARQL


# ---------------------------------------------------------------------------
# Schémas Pydantic -- RMES_run_sparql
# ---------------------------------------------------------------------------

class RunSparqlInput(BaseModel):
    full_sparql_query: str = Field(
        description="Requête SPARQL complète (SELECT / ASK / CONSTRUCT / DESCRIBE).",
    )
    timeout: float = Field(
        default=DEFAULT_TIMEOUT,
        description=f"Timeout en secondes (plafonné à {MAX_TIMEOUT}s).",
        gt=0,
    )
    max_rows: int = Field(
        default=DEFAULT_ROW_LIMIT,
        description=f"Limite de lignes ajoutée si absente de la requête (plafonnée à {MAX_ROW_LIMIT}).",
        ge=1,
        le=MAX_ROW_LIMIT,
    )


class RunSparqlOutput(BaseModel):
    format: Literal["json", "turtle"] = "json"
    limit_added: Optional[int] = None
    hint: Optional[str] = None
    # Résultats SELECT/ASK : variables déclarées + lignes brutes (bindings SPARQL JSON).
    # On garde les lignes en dict libre plutôt que de les typer entièrement : les
    # variables retournées dépendent entièrement de la requête SPARQL de l'appelant,
    # les figer dans un schéma fixe serait soit incomplet, soit un schéma générique
    # sans valeur ajoutée par rapport à un dict.
    variables: Optional[list[str]] = None
    bindings: Optional[list[dict[str, Any]]] = None
    # Résultat CONSTRUCT/DESCRIBE
    turtle: Optional[str] = None
    error: Optional[SparqlError] = None


# ---------------------------------------------------------------------------
# Enregistrement du tool MCP
# ---------------------------------------------------------------------------

def register_rmes_run_sparql(mcp: FastMCP) -> None:

    @mcp.tool(
        name=RMES_RUN_SPARQL["tool_name"],
        description=RMES_RUN_SPARQL["tool_description"] + "\n" + KNOWN_VOCABULARIES_NOTE + "\n\n"
        "Exemple -- recherche de codes NAF contenant \"extraction\" :\n"
        "PREFIX skos: <http://www.w3.org/2004/02/skos/core#>\n"
        "SELECT ?s ?label WHERE {\n"
        "  GRAPH <http://rdf.insee.fr/graphes/codes/naf2025> {\n"
        "    ?s skos:prefLabel ?label .\n"
        "    FILTER(lang(?label) = \"fr\")\n"
        "    FILTER(CONTAINS(LCASE(STR(?label)), \"extraction\"))\n"
        "  }\n"
        "} LIMIT 10\n"
        "\n"
        "Les requêtes CONSTRUCT/DESCRIBE renvoient du Turtle (`format=\"turtle\"`, champ `turtle`) "
        "plutôt que des lignes (`format=\"json\"`, champs `variables`/`bindings`).",
        meta=RMES_RUN_SPARQL["tool_metadata"],
    )
    @log_tool
    async def run_sparql(params: RunSparqlInput) -> RunSparqlOutput:
        if not params.full_sparql_query or not params.full_sparql_query.strip():
            return RunSparqlOutput(
                error=SparqlError(
                    type=SparqlErrorType.EMPTY_QUERY,
                    message="La requête est vide.",
                    query=params.full_sparql_query,
                )
            )

        max_rows = max(1, min(params.max_rows, MAX_ROW_LIMIT))
        result = await _execute_sparql(params.full_sparql_query, timeout=params.timeout, max_rows=max_rows)

        if "error" in result:
            return RunSparqlOutput(error=SparqlError(**result["error"]))

        if result.get("format") == "turtle":
            return RunSparqlOutput(
                format="turtle", limit_added=result.get("limit_added") and max_rows, turtle=result["data"]
            )

        meta = result.get("_meta", {})
        return RunSparqlOutput(
            format="json",
            limit_added=meta.get("limit_added"),
            hint=meta.get("hint"),
            variables=result.get("head", {}).get("vars"),
            bindings=result.get("results", {}).get("bindings"),
        )
