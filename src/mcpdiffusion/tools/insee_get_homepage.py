"""Tool: get_insee_homepage -- thin registration layer."""

from fastmcp import FastMCP

from ..data.indicators import KEY_INDICATORS
from ..models.insee import KeyIndicatorsOutput
from ..services.insee_indicators import build_key_indicators


# Business rule: the docstring below calls the figures "latest" and the instructions make this tool the
# preferred FIRST step, but they are frozen literals (see data/indicators.py). Whether the wording softens
# or the data becomes live is the same decision. Left as-is deliberately.
def register_get_insee_homepage(mcp: FastMCP) -> None:
    @mcp.tool
    def get_insee_homepage() -> KeyIndicatorsOutput:
        """Retrieve the INSEE home page with the latest key indicators at national level published by
        the institute (population, inflation, unemployment, GDP growth, ...).

        Each indicator carries a `value` that is a full sentence in French stating the figure and the
        period it covers.
        """
        return build_key_indicators(KEY_INDICATORS)
