"""Pydantic schemas for the feedback tool."""
from __future__ import annotations

from pydantic import BaseModel, Field


class SendFeedbackInput(BaseModel):
    username: str = Field(
        description="Identifier for the feedback author (e.g., user name, role, or session ID).",
        examples=["alice", "data_analyst", "session_abc123"],
    )
    feedback: str = Field(
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
    )


class SendFeedbackOutput(BaseModel):
    status: str = "success"
    message: str
    timestamp: str
