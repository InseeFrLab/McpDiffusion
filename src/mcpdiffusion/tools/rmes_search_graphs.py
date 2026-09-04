"""Tool: search_rmes_graphs -- thin registration layer."""

from __future__ import annotations

from fastmcp import Context, FastMCP

from ..infra.sparql import get_sparql_http_client
from ..models.rmes import (
    ExpandGraphs,
    GraphCategory,
    GraphCategoryChoice,
    GraphsOutput,
    GraphUriSubstring,
)
from ..services.rmes import search_rmes_graphs_service


def register_search_rmes_graphs(mcp: FastMCP, *, endpoint: str) -> None:
    @mcp.tool
    async def search_rmes_graphs(
        ctx: Context,
        graph_uri_substring: GraphUriSubstring = None,
        graph_category: GraphCategory = GraphCategoryChoice.ALL,
        expand_graphs: ExpandGraphs = False,
    ) -> GraphsOutput:
        """Liste les graphes nommes disponibles dans la base RDF de l'INSEE (RMES).

        Par defaut (`graph_category=ALL`), le resultat est une vue CONDENSEE par categorie, avec un
        compteur et quelques URIs d'exemple par categorie -- pas la liste plate des 700+ graphes.
        Choisis une categorie precise dans le parametre `graph_category` pour cibler une famille, ou
        utilise `graph_uri_substring` pour une recherche libre par sous-chaine. Une categorie "autre" recueille
        tout graphe ne correspondant a aucune famille connue.
        """
        return await search_rmes_graphs_service(
            graph_uri_substring=graph_uri_substring,
            graph_category=graph_category,
            expand_graphs=expand_graphs,
            sparql_client=get_sparql_http_client(ctx),
            endpoint=endpoint,
        )
