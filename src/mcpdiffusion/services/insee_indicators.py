"""Business logic for the INSEE key indicators tool."""

from ..models.insee import KeyIndicatorsOutput, KeyValueIndicator


def build_key_indicators(entries: list[dict[str, str]]) -> KeyIndicatorsOutput:
    indicators = [
        KeyValueIndicator(
            key=entry["cle"],
            alias=entry["alias"],
            value=entry["valeur"],
        )
        for entry in entries
    ]
    return KeyIndicatorsOutput(
        indicators=indicators,
        count=len(indicators),
    )
