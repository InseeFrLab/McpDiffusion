"""Tool registration entrypoint.

The only place that knows about the MCP server. Each group -- the three data sources, and the
feedback tool -- is registered only when its flag is on: an unregistered tool is the one kind of
"disabled" the protocol guarantees, unlike tag or visibility filtering, which a later call can undo.

Every tool is a plain function, so none of them carries a registration wrapper. Those that need a
service take it through `Depends`; `send_feedback` needs none.
"""

from __future__ import annotations

from fastmcp import FastMCP

from ..settings import Settings
from .insee.get_document_tool import get_insee_document
from .insee.get_homepage_tool import get_insee_homepage
from .insee.search_chiffrecle_tool import search_insee_chiffrecle
from .insee.search_conjoncture_tool import search_insee_conjoncture
from .insee.search_documents_tool import search_insee_documents
from .melodi.get_observations_tool import get_melodi_observations
from .melodi.search_datasets_tool import search_melodi_datasets
from .melodi.search_modalities_tool import search_melodi_modalities
from .rmes.describe_resource_tool import describe_rmes_resource
from .rmes.run_sparql_tool import run_rmes_sparql
from .rmes.search_graphs_tool import search_rmes_graphs
from .send_feedback_tool import send_feedback


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
        mcp.add_tool(search_rmes_graphs)
        mcp.add_tool(describe_rmes_resource)
        mcp.add_tool(run_rmes_sparql)

    if settings.enable_feedback_tool:
        mcp.add_tool(send_feedback)
