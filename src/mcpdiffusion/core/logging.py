"""Structured logging config + per-tool decorator."""
from __future__ import annotations

import functools
import inspect
import logging
import time
from typing import Any, Callable, TypeVar

from ..config.settings import get_settings

_settings = get_settings()

MAIN_LOGGER_NAME = "mcp.main"

logging.basicConfig(
    level=_settings.log_level,
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
        "level": _settings.log_level,
        "handlers": ["default"],
    },
}

TOOLS_LOGGER_NAME = "mcp.tools"
logger = logging.getLogger(TOOLS_LOGGER_NAME)


_F = TypeVar("_F", bound=Callable[..., Any])

_SCRUB_FIELDS = {"password", "mdp", "token", "secret", "auth", "api_key"}
_KWARGS_PREVIEW_LIMIT = 800


def _scrub(kwargs: dict) -> str:
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
    if result is None:
        return 0
    if isinstance(result, (list, tuple)):
        return len(result)
    if isinstance(result, dict):
        if "results" in result and isinstance(result["results"], list):
            return len(result["results"])
        if "count" in result:
            return result["count"]
    r = getattr(result, "results", None)
    if isinstance(r, list):
        return len(r)
    return None


def log_tool(func: _F) -> _F:
    """Decorator that logs entry, exit (duration + count) and errors."""
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

    wrapper.__signature__ = inspect.signature(func)  # type: ignore[attr-defined]
    return wrapper  # type: ignore[return-value]
