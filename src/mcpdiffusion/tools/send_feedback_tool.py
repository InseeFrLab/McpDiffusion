"""Tool: send_feedback."""

from ..models.feedback import Author, Feedback, FeedbackOutput
from ..services.feedback import record_feedback


def send_feedback(
    author: Author,
    feedback: Feedback,
) -> FeedbackOutput:
    """Report a problem or a suggestion about this server's tools to the people who maintain it.

    Returns a confirmation carrying the timestamp under which the feedback was recorded.

    WHEN TO USE
    - A tool failed, returned an empty result you have good reason to think is wrong, or its description led you
      to the wrong call. Say which tool and what you expected.

    WHEN NOT TO USE
    - To answer the person you are talking to. It reaches the server maintainers, not them.
    - To keep notes for yourself, or to acknowledge a call that worked.
    """
    return record_feedback(
        author=author,
        feedback=feedback,
    )
