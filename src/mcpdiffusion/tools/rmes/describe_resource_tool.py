"""Tool: describe_rmes_resource."""

from __future__ import annotations

from fastmcp.dependencies import Depends

from ...dependencies import get_rmes_graph_store_service
from ...models.rmes import GraphUri, ResourceOutput, ResourceUri
from ...services.rmes.graph_store_service import RmesGraphStoreService


async def describe_rmes_resource(
    resource_uri: ResourceUri,
    graph_uri: GraphUri = None,
    rmes_graph_store_service: RmesGraphStoreService = Depends(get_rmes_graph_store_service),
) -> ResourceOutput:
    """Recupere toutes les proprietes connues (predicat -> valeur) d'une ressource RDF identifiee
    par son URI complete. Combine automatiquement les proprietes ou la ressource est sujet ET
    celles ou elle est objet (utile pour remonter des relations skos:broader par exemple).
    Restreins avec `graph_uri` si tu sais deja ou chercher -- sinon la recherche se fait sur tous les
    graphes, ce qui est plus lent.
    """
    properties = await rmes_graph_store_service.describe_resource(
        resource_uri=resource_uri,
        graph_uri=graph_uri,
    )
    return ResourceOutput(
        uri=resource_uri,
        properties=properties,
        count=len(properties),
    )
