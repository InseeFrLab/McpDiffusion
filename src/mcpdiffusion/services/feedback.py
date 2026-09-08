"""Business logic for the feedback tool."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ..models.feedback import FeedbackOutput

# Fixme: this is extremely hacky, and feedback gets tied to the running instance
_FEEDBACK_DIR = Path(__file__).resolve().parent.parent / "feedback"
_FEEDBACK_FILE = _FEEDBACK_DIR / "feedback.md"


# Fixme: this function writes files within the running container, this is a major side effect
# Fixme: also check where this code is invoked, because if in the event loop, it is blocking
# Fixme: those kind of checks belong at the app startup, for example in a lifespan function
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


# Fixme: I am wondering where the author come from, because if sent by the client, this can be messed up
# Fixme: Also wondering if there is a cap on the author size of the feedback content,
#  it can make the container write uncontrolled amount of data
async def send_feedback_service(
    author: str,
    feedback: str,
) -> FeedbackOutput:
    feedback_path = _ensure_feedback_file()
    # Fixme: there is no timezone here, while at some in the code we consider timezones
    #   it seems a bit inconsistent
    recorded_at = datetime.now()

    # Fixme: prefer more readable multiline strings
    entry = (
        # Fixme: again, people can insert anything and forge data into the feedback file
        #   just hope this is not ultimately fed to an LLM
        # Fixme: a big flaw is that feedback.md is versioned, so user feedback might be fed into git
        # Fixme: beware the data is lost on each restart
        f"## {recorded_at.isoformat(timespec='seconds')} — {author}\n\n{feedback}\n\n---\n\n"
    )

    # Fixme: this call is blocking the event loop
    #   consider using aiofiles instead
    with feedback_path.open("a", encoding="utf-8") as f:
        f.write(entry)

    return FeedbackOutput(
        message="Feedback recorded successfully.",
        timestamp=recorded_at,
    )
