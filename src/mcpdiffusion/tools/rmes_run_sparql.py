"""Tool: RMES_run_sparql -- thin registration layer."""

from __future__ import annotations

from fastmcp import Context, FastMCP

from ..config.tool_metadata import RMES_RUN_SPARQL
from ..infra.sparql import get_sparql_http_client
from ..models.rmes import RunSparqlInput, RunSparqlOutput
from ..services.rmes import KNOWN_VOCABULARIES_NOTE, run_sparql


def register_rmes_run_sparql(mcp: FastMCP, *, endpoint: str) -> None:
    @mcp.tool(
        name=RMES_RUN_SPARQL["tool_name"],
        # Fixme: this description combinaison involves too many sources of data, the metadata file,
        #  the service plus a hardoded description
        # Fixme: this is also not the right place for a query
        description=RMES_RUN_SPARQL["tool_description"] + "\n" + KNOWN_VOCABULARIES_NOTE + "\n\n"
        'Exemple -- recherche de codes NAF contenant "extraction" :\n'
        "PREFIX skos: <http://www.w3.org/2004/02/skos/core#>\n"
        "SELECT ?s ?label WHERE {\n"
        "  GRAPH <http://rdf.insee.fr/graphes/codes/naf2025> {\n"
        "    ?s skos:prefLabel ?label .\n"
        '    FILTER(lang(?label) = "fr")\n'
        '    FILTER(CONTAINS(LCASE(STR(?label)), "extraction"))\n'
        "  }\n"
        "} LIMIT 10\n"
        "\n"
        'Les requetes CONSTRUCT/DESCRIBE renvoient du Turtle (`format="turtle"`, champ `turtle`) '
        'plutot que des lignes (`format="json"`, champs `variables`/`bindings`).',
        meta=RMES_RUN_SPARQL["tool_metadata"],
    )
    async def run_sparql_tool(params: RunSparqlInput, ctx: Context) -> RunSparqlOutput:
        return await run_sparql(
            params,
            sparql_client=get_sparql_http_client(ctx),
            endpoint=endpoint,
        )
