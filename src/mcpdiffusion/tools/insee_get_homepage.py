"""Tool: get_insee_homepage -- thin registration layer."""

from fastmcp import FastMCP

from ..config.tool_metadata import GET_HOMEPAGE
from ..data.indicators import KEY_INDICATORS
from ..models.insee import KeyIndicatorsOutput
from ..services.insee_indicators import build_key_indicators


def register_get_insee_homepage(mcp: FastMCP) -> None:
    @mcp.tool(
        name=GET_HOMEPAGE["tool_name"],
        description=GET_HOMEPAGE["tool_description"],
        meta=GET_HOMEPAGE["tool_metadata"],
    )
    def get_insee_homepage() -> KeyIndicatorsOutput:
        return build_key_indicators(KEY_INDICATORS)
