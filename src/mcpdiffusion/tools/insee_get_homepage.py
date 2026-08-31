"""Tool: get_insee_homepage -- thin registration layer."""
from __future__ import annotations

from fastmcp import FastMCP

from ..config.tool_metadata import GET_HOMEPAGE
from ..core.logging import log_tool
from ..data.indicators import DICT_KV
from ..models.insee import KeyIndicatorsOutput, KeyValueIndicator

# Fixme: the tool contains no service which is kind of breaking the convention I saw earlier
#   this correlates unit testing to the tool mechanics
def register_get_insee_homepage(mcp: FastMCP) -> None:
    @mcp.tool(
        name=GET_HOMEPAGE["tool_name"],
        description=GET_HOMEPAGE["tool_description"],
        meta=GET_HOMEPAGE["tool_metadata"],
    )
    # Fixme: this is an async function with nothing to await
    @log_tool
    async def get_insee_homepage() -> KeyIndicatorsOutput:
        indicators = [
            KeyValueIndicator(
                key=entry["cle"].strip(),
                alias=entry["alias"].strip(),
                value=entry["valeur"].strip(),
            )
            for entry in DICT_KV
            if not (
                entry["cle"].strip() == "clé"
                and entry["alias"].strip() == "alias"
                and entry["valeur"].strip() == "valeur"
            )
        ]
        return KeyIndicatorsOutput(indicators=indicators, count=len(indicators))
