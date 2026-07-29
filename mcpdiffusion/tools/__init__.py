from mcp.server.fastmcp import FastMCP

from tools.INSEEFR_search_documents import register_search_insee_documents
from tools.INSEEFR_get_documents import register_get_insee_documents
from tools.INSEEFR_get_conjoncture import register_search_insee_conjoncture
from tools.INSEEFR_get_homepage import register_get_insee_homepage
from tools.MELODI_get_columns import register_get_columns
from tools.MELODI_get_dataset import register_get_datasets
from tools.MELODI_search_dataset import register_search_datasets
from tools.RMES_search_graph import register_RMES_search_graph


def register_tools(mcp: FastMCP) -> None:
    """Register all MCP tools with the provided FastMCP instance."""
    #INSEEFR
    register_search_insee_documents(mcp)
    register_get_insee_homepage(mcp)
    register_get_insee_documents(mcp)
    register_search_insee_conjoncture(mcp)
    

    #MELODI
    register_get_columns(mcp)
    register_get_datasets(mcp)
    register_search_datasets(mcp)

    #RMES
    register_RMES_search_graph(mcp)


