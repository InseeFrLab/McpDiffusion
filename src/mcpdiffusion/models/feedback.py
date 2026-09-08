"""Pydantic schemas for the feedback tool."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field

# ----------------------------------------------------------------------------------------------------------------------
# Schema bounds --------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------

# Both fields are client-supplied and land in the server log, so they are bounded here rather
# than trusted. Pydantic rejects an over-long value before any of it is recorded.
MAX_AUTHOR_CHARS = 100
MAX_FEEDBACK_CHARS = 10_000


# ----------------------------------------------------------------------------------------------------------------------
# Tool parameters ------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------

Author = Annotated[
    str,
    Field(
        description="Identifier for the feedback author (e.g., user name, role, or session ID).",
        max_length=MAX_AUTHOR_CHARS,
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
        max_length=MAX_FEEDBACK_CHARS,
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
