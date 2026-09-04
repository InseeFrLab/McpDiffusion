"""Pydantic schemas for the feedback tool."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field

# ----------------------------------------------------------------------------------------------------------------------
# Tool parameters ------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------

Author = Annotated[
    str,
    Field(
        description="Identifier for the feedback author (e.g., user name, role, or session ID).",
        examples=[
            "alice",
            "data_analyst",
            "session_abc123",
        ],
    ),
]

Feedback = Annotated[
    str,
    Field(
        description=(
            "Clear, actionable Markdown describing the issue or suggestion. Include context "
            "(which tool, what happened), expected vs actual behavior, and proposed solutions "
            "if applicable. Write as if filing a GitHub issue."
        ),
        examples=[
            "## Bug Report\n\n**Tool:** search_melodi_datasets\n\n**Issue:** No results returned "
            "for 'prix du pain' even though dataset DS_PRIX exists.\n\n**Expected:** Should find "
            "at least one matching dataset.\n\n**Proposed fix:** Check if the Elasticsearch index "
            "includes this dataset.",
        ],
    ),
]


# ----------------------------------------------------------------------------------------------------------------------
# Result models --------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------


class FeedbackOutput(BaseModel):
    status: Literal["success"] = "success"
    message: str
    timestamp: datetime
