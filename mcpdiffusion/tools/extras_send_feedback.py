"""Tool: send_feedback

Submit structured feedback about the MCP tools, server behavior, or user experience.
Feedback is appended to a timestamped Markdown file for administrator review.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fastmcp import FastMCP
from pydantic import BaseModel, Field

from helpers.logging import log_tool
from tools.env import SEND_FEEDBACK


# ---------------------------------------------------------------------------
# Schémas Pydantic -- send_feedback
# ---------------------------------------------------------------------------

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
    #path: str


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

# Resolve feedback file path relative to this module's location, not CWD.
# Structure: mcpdiffusion/tools/extras_send_feedback.py -> mcpdiffusion/feedback/feedback.md
_FEEDBACK_DIR = Path(__file__).resolve().parent.parent / "feedback"
_FEEDBACK_FILE = _FEEDBACK_DIR / "feedback.md"


def _ensure_feedback_file() -> Path:
    """Create feedback directory and seed file if they don't exist."""
    _FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)
    if not _FEEDBACK_FILE.exists():
        _FEEDBACK_FILE.write_text(
            "# Feedback Log\n\n"
            "This file collects feedback from users and the assistant about MCP tools, "
            "server behavior, and suggestions for improvement. Each entry is timestamped "
            "and formatted as Markdown for easy review.\n\n---\n\n",
            encoding="utf-8",
        )
    return _FEEDBACK_FILE


# ---------------------------------------------------------------------------
# Enregistrement du tool MCP
# ---------------------------------------------------------------------------

def register_extras_send_feedback(mcp: FastMCP) -> None:

    @mcp.tool(
        name=SEND_FEEDBACK["tool_name"],
        description=SEND_FEEDBACK["tool_description"],
        meta=SEND_FEEDBACK["tool_metadata"],
    )
    @log_tool
    async def send_feedback(params: SendFeedbackInput) -> SendFeedbackOutput:
        feedback_path = _ensure_feedback_file()
        timestamp = datetime.now().isoformat(timespec="seconds")

        # Format: ## heading with timestamp and username, then feedback body, then separator
        entry = (
            f"## {timestamp} — {params.username}\n\n"
            f"{params.feedback}\n\n"
            "---\n\n"
        )

        with feedback_path.open("a", encoding="utf-8") as f:
            f.write(entry)

        return SendFeedbackOutput(
            message=f"Feedback recorded successfully.",
            timestamp=timestamp,
            #path=str(feedback_path),
        )
