"""Logging configuration, applied once at startup."""

import logging
import logging.config

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"


def build_logging_config(level: str) -> dict:
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": LOG_FORMAT,
            },
        },
        "handlers": {
            "default": {
                "class": "logging.StreamHandler",
                "formatter": "default",
            },
        },
        "root": {
            "level": level,
            "handlers": ["default"],
        },
    }


def configure_logging(level: str) -> None:
    logging.config.dictConfig(build_logging_config(level))
