"""Tool: search_rmes_graphs."""

from fastmcp.dependencies import Depends

from ...dependencies.rmes import get_rmes_graph_store_service
from ...models.rmes import (
    ExpandGraphs,
    GraphCategory,
    GraphCategoryChoice,
    GraphsOutput,
    GraphUriSubstring,
)
from ...services.rmes.graph_store_service import RmesGraphStoreService
from ...services.rmes.graph_taxonomy import build_category_summary, filter_graph_rows


async def search_rmes_graphs(
    graph_uri_substring: GraphUriSubstring = None,
    graph_category: GraphCategory = GraphCategoryChoice.ALL,
    expand_graphs: ExpandGraphs = False,
    rmes_graph_store_service: RmesGraphStoreService = Depends(get_rmes_graph_store_service),
) -> GraphsOutput:
    """Liste les graphes nommes disponibles dans la base RDF de l'INSEE (RMES).

    Par defaut (`graph_category=ALL`), le resultat est une vue CONDENSEE par categorie, avec un
    compteur et quelques URIs d'exemple par categorie -- pas la liste plate des 700+ graphes.
    Choisis une categorie precise dans le parametre `graph_category` pour cibler une famille, ou
    utilise `graph_uri_substring` pour une recherche libre par sous-chaine. Une categorie "autre" recueille
    tout graphe ne correspondant a aucune famille connue.
    """
    rows = await rmes_graph_store_service.fetch_graph_rows()
    category = None if graph_category == GraphCategoryChoice.ALL else graph_category.value
    matched = filter_graph_rows(
        rows=rows,
        graph_uri_substring=graph_uri_substring,
        graph_category=category,
        graph_base_uri=rmes_graph_store_service.graph_base_uri,
    )
    # Narrowing the list means the caller wants to see it, not just a count per category.
    include_graphs = expand_graphs or bool(graph_uri_substring) or category is not None
    return GraphsOutput(
        total_graphs_matched=len(matched),
        categories=build_category_summary(
            rows=matched,
            include_graphs=include_graphs,
            graph_base_uri=rmes_graph_store_service.graph_base_uri,
        ),
    )
