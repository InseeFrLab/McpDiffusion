"""Tool registration entrypoint.

Each tool module exposes a `register_xxx(mcp: FastMCP)` function. This file
wires all of them in one place; to disable a tool, comment out its import
and the corresponding call below.
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
from .melodi_get_observations import register_get_melodi_observations
from .melodi_search_datasets import register_search_melodi_datasets
from .melodi_search_modalities import register_search_melodi_modalities
from .rmes_describe_resource import register_describe_rmes_resource
from .rmes_run_sparql import register_run_rmes_sparql
from .rmes_search_graphs import register_search_rmes_graphs


# Fixme: there might be better pattern instead of iterating with if statements on tool groups
def register_tools(mcp: FastMCP, settings: Settings) -> None:
    """Register the enabled tools, handing each the settings it needs."""
    if settings.enable_inseefr_tools:
        register_search_insee_documents(mcp, index=settings.es_index_produits)
        register_get_insee_homepage(mcp)
        register_get_insee_document(mcp)
        register_search_insee_conjoncture(mcp, index=settings.es_index_produits)
        register_search_insee_chiffrecle(mcp, index=settings.es_index_produits)

    if settings.enable_melodi_tools:
        register_search_melodi_datasets(mcp, index=settings.es_index_melodi_datasets)
        register_search_melodi_modalities(mcp, index=settings.es_index_melodi_columns)
        register_get_melodi_observations(mcp)

    if settings.enable_rmes_tools:
        register_search_rmes_graphs(mcp, endpoint=settings.rmes_endpoint)
        register_describe_rmes_resource(mcp, endpoint=settings.rmes_endpoint)
        register_run_rmes_sparql(mcp, endpoint=settings.rmes_endpoint)
