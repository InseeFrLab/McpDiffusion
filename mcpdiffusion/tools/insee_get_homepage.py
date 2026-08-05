"""Tool: get_insee_homepage

Return the curated set of INSEE key indicators (``DICT_KV`` from
``tools.env``) instead of scraping the INSEE homepage.
"""
from __future__ import annotations

from fastmcp import FastMCP
from pydantic import BaseModel, Field

from helpers.logging import log_tool
from tools.env import DICT_KV, GET_HOMEPAGE


class KeyValueIndicator(BaseModel):
    """A single INSEE key indicator with its pre-computed textual value."""

    key: str = Field(description="Indicator name (e.g. 'smic', 'PIB annuel').")
    alias: str = Field(
        default="",
        description="Optional alias / alternative name for the indicator.",
    )
    value: str = Field(
        description="Pre-computed textual description of the latest figure."
    )


class KeyIndicatorsOutput(BaseModel):
    """The curated list of INSEE key indicators (replaces the homepage
    scraping output)."""

    indicators: list[KeyValueIndicator] = Field(
        description="Curated key indicators: name, alias and latest value.",
    )
    count: int = Field(description="Number of indicators returned.")


def register_get_insee_homepage(mcp: FastMCP) -> None:
    @mcp.tool(
        name=GET_HOMEPAGE["tool_name"],
        description=GET_HOMEPAGE["tool_description"],
        meta=GET_HOMEPAGE["tool_metadata"],
    )
    @log_tool
    async def get_insee_homepage() -> KeyIndicatorsOutput:
        indicators = [
            KeyValueIndicator(
                key=entry["cle"].strip(),
                alias=entry["alias"].strip(),
                value=entry["valeur"].strip(),
            )
            for entry in DICT_KV
            # Skip the placeholder/header row shipped in DICT_KV.
            if not (
                entry["cle"].strip() == "clé"
                and entry["alias"].strip() == "alias"
                and entry["valeur"].strip() == "valeur"
            )
        ]
        return KeyIndicatorsOutput(indicators=indicators, count=len(indicators))
