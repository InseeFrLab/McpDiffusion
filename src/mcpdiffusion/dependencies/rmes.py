"""The RMES service a tool can be handed."""

from fastmcp import Context
from fastmcp.dependencies import CurrentContext

from ..services.rmes.graph_store_service import RmesGraphStoreService


def get_rmes_graph_store_service(ctx: Context = CurrentContext()) -> RmesGraphStoreService:
    """Return the RMES graph store service built at startup."""
    return ctx.lifespan_context["rmes_graph_store_service"]
