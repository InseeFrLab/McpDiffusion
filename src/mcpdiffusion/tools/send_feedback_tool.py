"""Tool: send_feedback."""

from ..models.feedback import Author, Feedback, FeedbackOutput
from ..services.feedback import record_feedback


def send_feedback(
    author: Author,
    feedback: Feedback,
) -> FeedbackOutput:
    """Report a problem or a suggestion about this server's tools to the people who maintain it.

    Use it when a tool failed, returned an empty result you have good reason to think is wrong, or
    carried a description that led you to the wrong call. The entry reaches the server operators,
    not the person you are talking to, so it is not a way to answer them.

    Returns a confirmation carrying the timestamp under which the feedback was recorded.
    """
    return record_feedback(
        author=author,
        feedback=feedback,
    )
