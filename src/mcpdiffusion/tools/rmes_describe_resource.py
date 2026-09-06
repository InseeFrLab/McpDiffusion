"""Tool: describe_rmes_resource -- thin registration layer."""

from __future__ import annotations

from fastmcp import Context, FastMCP

from ..dependencies import get_sparql_http_client
from ..models.rmes import GraphUri, ResourceOutput, ResourceUri
from ..services.rmes import describe_rmes_resource_service


def register_describe_rmes_resource(mcp: FastMCP, *, endpoint: str) -> None:
    @mcp.tool
    async def describe_rmes_resource(
        ctx: Context,
        resource_uri: ResourceUri,
        graph_uri: GraphUri = None,
    ) -> ResourceOutput:
        """Recupere toutes les proprietes connues (predicat -> valeur) d'une ressource RDF identifiee
        par son URI complete. Combine automatiquement les proprietes ou la ressource est sujet ET
        celles ou elle est objet (utile pour remonter des relations skos:broader par exemple).
        Restreins avec `graph_uri` si tu sais deja ou chercher -- sinon la recherche se fait sur tous les
        graphes, ce qui est plus lent.
        """
        return await describe_rmes_resource_service(
            resource_uri=resource_uri,
            graph_uri=graph_uri,
            sparql_client=get_sparql_http_client(ctx),
            endpoint=endpoint,
        )
