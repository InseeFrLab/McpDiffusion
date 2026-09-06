"""Tool: get_insee_homepage."""

from __future__ import annotations

from ...data.insee.indicators import KEY_INDICATORS
from ...models.insee import KeyIndicatorsOutput, KeyValueIndicator


# Business rule: the docstring below calls the figures "latest" and the instructions make this tool the
# preferred FIRST step, but they are frozen literals (see data/insee/indicators.py). Whether the wording softens
# or the data becomes live is the same decision. Left as-is deliberately.
def get_insee_homepage() -> KeyIndicatorsOutput:
    """Retrieve the INSEE home page with the latest key indicators at national level published by
    the institute (population, inflation, unemployment, GDP growth, ...).

    Each indicator carries a `value` that is a full sentence in French stating the figure and the
    period it covers.
    """
    indicators = [
        KeyValueIndicator(
            key=entry["cle"],
            alias=entry["alias"],
            value=entry["valeur"],
        )
        for entry in KEY_INDICATORS
    ]
    return KeyIndicatorsOutput(
        indicators=indicators,
        count=len(indicators),
    )
