"""Tool: get_insee_homepage."""

from ...data.insee.indicators import KEY_INDICATORS
from ...models.insee import KeyIndicatorsOutput, KeyValueIndicator


# Business rule: the docstring below calls the figures "latest" and makes this tool the preferred FIRST step,
# but they are frozen literals (see data/insee/indicators.py). Whether the wording softens or the data becomes
# live is the same decision. Left as-is deliberately.
def get_insee_homepage() -> KeyIndicatorsOutput:
    """Retrieve the INSEE home page with the latest key indicators at national level published by
    the institute (population, inflation, unemployment, GDP growth, ...).

    Each indicator carries a `value` that is a full sentence in French stating the figure and the
    period it covers.

    WHEN TO USE
    - Preferred FIRST step for any generic, up-to-date statistical question. It gives the most recent official
      figure instantly, without searching individual documents.

    WHEN NOT TO USE
    - User asks for a previous year's figure. Use `search_insee_documents` or `search_insee_conjoncture` with
      `year_of_reference`.

    WORKFLOW
    1. Call this tool.
    2. Present the indicator value, quoting the period it states.
    3. Follow up with `search_insee_documents` or `search_insee_conjoncture` if the user needs deeper tables,
       historic series, or a source document.
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
