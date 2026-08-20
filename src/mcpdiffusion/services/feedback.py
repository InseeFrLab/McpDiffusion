"""Business logic for the feedback tool."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ..models.feedback import SendFeedbackInput, SendFeedbackOutput

_FEEDBACK_DIR = Path(__file__).resolve().parent.parent / "feedback"
_FEEDBACK_FILE = _FEEDBACK_DIR / "feedback.md"


def _ensure_feedback_file() -> Path:
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


async def send_feedback(params: SendFeedbackInput) -> SendFeedbackOutput:
    feedback_path = _ensure_feedback_file()
    timestamp = datetime.now().isoformat(timespec="seconds")

    entry = (
        f"## {timestamp} — {params.username}\n\n"
        f"{params.feedback}\n\n"
        "---\n\n"
    )

    with feedback_path.open("a", encoding="utf-8") as f:
        f.write(entry)

    return SendFeedbackOutput(
        message="Feedback recorded successfully.",
        timestamp=timestamp,
    )
