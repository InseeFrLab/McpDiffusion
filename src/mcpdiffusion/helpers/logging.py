"""
Structured logging config + per-tool decorator.

- `MAIN_LOGGER_NAME` (`mcp.main`) is the application root.
- `TOOLS_LOGGER_NAME` (`mcp.tools`) is the tool-call stream.
- `@log_tool` works for both sync and async tool functions and emits:
    * entry (tool name + kwargs preview, secrets scrubbed)
    * exit  (duration ms, result count when applicable)
    * error (error code + short message)
"""
from __future__ import annotations

import functools
import inspect
import logging
import os
import time
from typing import Any, Callable, TypeVar


MAIN_LOGGER_NAME = "mcp.main"

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    force=True,
)

UVICORN_LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        }
    },
    "handlers": {
        "default": {
            "class": "logging.StreamHandler",
            "formatter": "default",
        }
    },
    "root": {
        "level": os.getenv("LOG_LEVEL", "INFO"),
        "handlers": ["default"],
    },
}

TOOLS_LOGGER_NAME = "mcp.tools"
logger = logging.getLogger(TOOLS_LOGGER_NAME)


_F = TypeVar("_F", bound=Callable[..., Any])


# Fields whose values we never want to log in plain text.
_SCRUB_FIELDS = {"password", "mdp", "token", "secret", "auth", "api_key"}
_KWARGS_PREVIEW_LIMIT = 800


def _scrub(kwargs: dict) -> str:
    """Return a bounded, redacted repr of kwargs suitable for logs."""
    safe = {}
    for k, v in kwargs.items():
        if any(s in k.lower() for s in _SCRUB_FIELDS):
            safe[k] = "***"
        else:
            safe[k] = v
    text = repr(safe)
    if len(text) > _KWARGS_PREVIEW_LIMIT:
        return text[:_KWARGS_PREVIEW_LIMIT] + "...<truncated>"
    return text


def _result_count(result: Any) -> int | None:
    """Best-effort count for result preview. None if unknown shape."""
    if result is None:
        return 0
    if isinstance(result, (list, tuple)):
        return len(result)
    if isinstance(result, dict):
        if "results" in result and isinstance(result["results"], list):
            return len(result["results"])
        if "count" in result:
            return result["count"]
    # Pydantic models with a .results attribute.
    r = getattr(result, "results", None)
    if isinstance(r, list):
        return len(r)
    return None


def log_tool(func: _F) -> _F:
    """Decorator that logs entry, exit (duration + count) and errors.

    Supports both sync and async tool functions. The FastMCP tool registry
    expects the decorated function to have the original signature; we
    preserve it via `inspect.signature`.
    """
    is_async = inspect.iscoroutinefunction(func)
    name = func.__name__

    def _log_exit(duration_ms: float, result: Any) -> None:
        count = _result_count(result)
        if count is None:
            logger.info("Tool exit: %s | %.1fms", name, duration_ms)
        else:
            logger.info(
                "Tool exit: %s | %.1fms | count=%d", name, duration_ms, count
            )

    def _log_error(duration_ms: float, exc: BaseException) -> None:
        code = getattr(exc, "args", ("",))[0] if exc.args else type(exc).__name__
        logger.error(
            "Tool error: %s | %.1fms | %s: %s",
            name, duration_ms, type(exc).__name__, str(code)[:200],
        )

    if is_async:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger.info("Tool call: %s | kwargs=%s", name, _scrub(kwargs))
            start = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
            except BaseException as exc:
                _log_error((time.perf_counter() - start) * 1000, exc)
                raise
            _log_exit((time.perf_counter() - start) * 1000, result)
            return result
        wrapper: Callable[..., Any] = async_wrapper
    else:
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            logger.info("Tool call: %s | kwargs=%s", name, _scrub(kwargs))
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
            except BaseException as exc:
                _log_error((time.perf_counter() - start) * 1000, exc)
                raise
            _log_exit((time.perf_counter() - start) * 1000, result)
            return result
        wrapper = sync_wrapper

    # Preserve the original signature for FastMCP introspection.
    wrapper.__signature__ = inspect.signature(func)  # type: ignore[attr-defined]
    return wrapper  # type: ignore[return-value]
