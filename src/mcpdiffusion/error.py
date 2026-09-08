"""The single error type tools and services raise."""

from enum import StrEnum

from fastmcp.exceptions import ToolError


class ErrorCode(StrEnum):
    """The closed vocabulary of failures a caller can be told about.

    A member rather than a `Literal`: a literal is only a promise to a type checker, so a typo
    reached the caller as an invented code. Referencing a member fails at the typo instead.
    """

    INVALID_INPUT = "INVALID_INPUT"
    BACKEND_UNAVAILABLE = "BACKEND_UNAVAILABLE"
    UPSTREAM_ERROR = "UPSTREAM_ERROR"
    PARSE_ERROR = "PARSE_ERROR"
    INVALID_QUERY = "INVALID_QUERY"
    NOT_FOUND = "NOT_FOUND"
    # A fault in this server rather than in the caller's input or a backend: a bug, logged
    # in full server-side and reported to the caller only as ours to fix.
    INTERNAL_ERROR = "INTERNAL_ERROR"


class AppToolError(ToolError):
    """A failure the caller is meant to read and act on.

    Subclasses ToolError, so the message survives `mask_error_details`. Every other exception is
    a bug and gets replaced by a generic message. The code and retryability are attributes for
    logging and tests, and are rendered into the message because that text is all the caller gets.

    The message must name what failed, why, and what to do next — the offending parameter, or the
    tool that produces a valid value.
    """

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        *,
        retryable: bool = False,
    ) -> None:
        self.code = code
        self.retryable = retryable
        marker = f"{code}, retryable" if retryable else code
        super().__init__(f"[{marker}] {message}")
