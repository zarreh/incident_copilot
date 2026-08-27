from __future__ import annotations

import structlog
from zarreh_agentkit.observability import get_logger as get_logger

__all__ = ["configure_logging", "get_logger"]


def configure_logging(environment: str) -> None:
    """Configure structlog: pretty console in dev, JSON in production."""
    renderer = (
        structlog.dev.ConsoleRenderer()
        if environment == "development"
        else structlog.processors.JSONRenderer()
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            renderer,
        ],
    )
