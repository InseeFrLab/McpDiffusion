"""Tool registration entrypoint.

The only place that knows about the MCP server. A family is registered only when its flag is on:
an unregistered tool is the one kind of "disabled" the protocol guarantees, unlike tag or
visibility filtering, which a later call can undo.

insee and Melodi tools are plain functions taking their service through `Depends`, so they carry
no registration wrapper. rmes still binds its endpoint through a `register_xxx` closure.
"""

from __future__ import annotations

from fastmcp import FastMCP

from ..settings import Settings

# Imported but never registered: send_feedback is not exposed. Decide whether to wire it up or
# drop it, then remove this import or the noqa.
from .feedback_send import register_send_feedback  # noqa: F401
from .insee.get_document_tool import get_insee_document
from .insee.get_homepage_tool import get_insee_homepage
from .insee.search_chiffrecle_tool import search_insee_chiffrecle
from .insee.search_conjoncture_tool import search_insee_conjoncture
from .insee.search_documents_tool import search_insee_documents
from .melodi.get_observations_tool import get_melodi_observations
from .melodi.search_datasets_tool import search_melodi_datasets
from .melodi.search_modalities_tool import search_melodi_modalities
from .rmes_describe_resource import register_describe_rmes_resource
from .rmes_run_sparql import register_run_rmes_sparql
from .rmes_search_graphs import register_search_rmes_graphs


def register_tools(mcp: FastMCP, settings: Settings) -> None:
    """Register the enabled tools, handing each the settings it needs."""
    if settings.enable_inseefr_tools:
        mcp.add_tool(search_insee_documents)
        mcp.add_tool(get_insee_homepage)
        mcp.add_tool(get_insee_document)
        mcp.add_tool(search_insee_conjoncture)
        mcp.add_tool(search_insee_chiffrecle)

    if settings.enable_melodi_tools:
        mcp.add_tool(search_melodi_datasets)
        mcp.add_tool(search_melodi_modalities)
        mcp.add_tool(get_melodi_observations)

    if settings.enable_rmes_tools:
        register_search_rmes_graphs(mcp, endpoint=settings.rmes_endpoint)
        register_describe_rmes_resource(mcp, endpoint=settings.rmes_endpoint)
        register_run_rmes_sparql(mcp, endpoint=settings.rmes_endpoint)
