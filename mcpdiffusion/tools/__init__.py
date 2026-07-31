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
from tools.rmes_query import register_query_insee_rmes


def register_tools(mcp: FastMCP) -> None:
    """Register all MCP tools with the given FastMCP instance."""
    # INSEE.fr
    register_search_insee_documents(mcp)
    register_get_insee_homepage(mcp)
    register_get_insee_document(mcp)
    register_search_insee_conjoncture(mcp)

    # Melodi
    register_search_melodi_datasets(mcp)
    register_search_melodi_modalities(mcp)
    register_get_melodi_observations(mcp)

    # RMES (SPARQL)
    register_query_insee_rmes(mcp)
