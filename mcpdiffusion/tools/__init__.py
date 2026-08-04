"""Tool registration entrypoint.

Each tool module exposes a `register_xxx(mcp: FastMCP)` function. This file
wires all of them in one place; to disable a tool, comment out its import
and the corresponding call below.
"""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from tools.melodi_get_observations import register_get_melodi_observations
from tools.melodi_search_datasets import register_search_melodi_datasets
from tools.melodi_search_modalities import register_search_melodi_modalities
from tools.insee_get_document import register_get_insee_document
from tools.insee_get_homepage import register_get_insee_homepage
from tools.insee_search_documents import register_search_insee_documents
from tools.insee_search_conjoncture import register_search_insee_conjoncture
from tools.insee_search_chiffrecle import register_search_insee_chiffreclef
from tools.rmes_list_graphs import register_rmes_list_graphs
from tools.rmes_describe_resource import register_rmes_describe_resource
from tools.rmes_run_sparql import register_rmes_run_sparql
from tools.extras_send_feedback import register_extras_send_feedback

def register_tools(mcp: FastMCP, toollist:str|None=None) -> None:
    """Register all MCP tools with the given FastMCP instance."""
    # INSEE.fr
    if toollist==("insee"):
        register_search_insee_documents(mcp)
        register_get_insee_homepage(mcp)
        register_get_insee_document(mcp)
        register_search_insee_conjoncture(mcp)
        register_search_insee_chiffreclef(mcp)

    # Melodi
    if toollist==("melodi"):
        register_search_melodi_datasets(mcp)
        register_search_melodi_modalities(mcp)
        register_get_melodi_observations(mcp)

    # RMES (SPARQL)
    if toollist==("rmes"):
        register_rmes_list_graphs(mcp)
        register_rmes_describe_resource(mcp)
        register_rmes_run_sparql(mcp)

    else:
        register_search_insee_documents(mcp)
        register_get_insee_homepage(mcp)
        register_get_insee_document(mcp)
        register_search_insee_conjoncture(mcp)
        register_search_insee_chiffreclef(mcp)
        register_search_melodi_datasets(mcp)
        register_search_melodi_modalities(mcp)
        register_get_melodi_observations(mcp)
        register_rmes_list_graphs(mcp)
        register_rmes_describe_resource(mcp)
        register_rmes_run_sparql(mcp)
        register_extras_send_feedback(mcp)