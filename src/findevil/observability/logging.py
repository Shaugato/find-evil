"""Structured logging via structlog + stdlib logging (blueprint Part 14.3).

All logs emit JSON on stdout so systemd-journald can ingest and Vector/Loki can
scrape without a custom parser. Every log line carries host_id + service fields.
"""

from __future__ import annotations

import logging
import sys

import structlog

from findevil.config.settings import settings

_configured = False


def configure_logging(service: str, level: str = "INFO") -> None:
    """Idempotent structlog + stdlib logging init."""
    global _configured
    if _configured:
        return
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper(), logging.INFO),
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper(), logging.INFO)
        ),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    structlog.contextvars.bind_contextvars(service=service, host_id=settings.host_id)
    _configured = True


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    if not _configured:
        configure_logging(service="findevil")
    return structlog.get_logger(name)
