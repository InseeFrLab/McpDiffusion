"""Tool registration entrypoint.

The only place that knows about the MCP server. A family is registered only when its flag is on:
an unregistered tool is the one kind of "disabled" the protocol guarantees, unlike tag or
visibility filtering, which a later call can undo.

Melodi tools are plain functions taking their service through `Depends`, so they carry no
registration wrapper. The other families still bind settings through a `register_xxx` closure.
"""

from __future__ import annotations

from fastmcp import FastMCP

from ..config.settings import Settings

# Imported but never registered: send_feedback is not exposed. Decide whether to wire it up or
# drop it, then remove this import or the noqa.
from .feedback_send import register_send_feedback  # noqa: F401
from .insee_get_document import register_get_insee_document
from .insee_get_homepage import register_get_insee_homepage
from .insee_search_chiffrecle import register_search_insee_chiffrecle
from .insee_search_conjoncture import register_search_insee_conjoncture
from .insee_search_documents import register_search_insee_documents
from .melodi.get_observations_tool import get_melodi_observations
from .melodi.search_datasets_tool import search_melodi_datasets
from .melodi.search_modalities_tool import search_melodi_modalities
from .rmes_describe_resource import register_describe_rmes_resource
from .rmes_run_sparql import register_run_rmes_sparql
from .rmes_search_graphs import register_search_rmes_graphs


def register_tools(mcp: FastMCP, settings: Settings) -> None:
    """Register the enabled tools, handing each the settings it needs."""
    if settings.enable_inseefr_tools:
        register_search_insee_documents(mcp, index=settings.es_index_produits)
        register_get_insee_homepage(mcp)
        register_get_insee_document(mcp)
        register_search_insee_conjoncture(mcp, index=settings.es_index_produits)
        register_search_insee_chiffrecle(mcp, index=settings.es_index_produits)

    if settings.enable_melodi_tools:
        mcp.add_tool(search_melodi_datasets)
        mcp.add_tool(search_melodi_modalities)
        mcp.add_tool(get_melodi_observations)

    if settings.enable_rmes_tools:
        register_search_rmes_graphs(mcp, endpoint=settings.rmes_endpoint)
        register_describe_rmes_resource(mcp, endpoint=settings.rmes_endpoint)
        register_run_rmes_sparql(mcp, endpoint=settings.rmes_endpoint)
