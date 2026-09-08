"""Business logic for the feedback tool."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from ..models.feedback import FeedbackOutput

logger = logging.getLogger(__name__)


def record_feedback(author: str, feedback: str) -> FeedbackOutput:
    """Record one feedback entry in the server log and confirm it to the caller.

    The log is the sink on purpose. A file written inside the container is lost on the next
    restart and reaches nobody; the log already goes wherever the operators are looking.

    Both fields come from the client, so they are JSON-encoded into the message. That keeps the
    entry on a single line and stops a crafted newline from forging a second one. The same values
    go in `extra` for aggregators that read structured fields rather than the rendered message.
    """
    recorded_at = datetime.now(UTC)
    logger.info(
        "Feedback received: author=%s body=%s",
        json.dumps(author),
        json.dumps(feedback),
        extra={
            "feedback_author": author,
            "feedback_body": feedback,
            "feedback_chars_count": len(feedback),
        },
    )
    return FeedbackOutput(
        message="Feedback recorded successfully.",
        timestamp=recorded_at,
    )
