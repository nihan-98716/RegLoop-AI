"""Structured logging configuration using structlog.

Wires structlog through the Python stdlib logging system so that
uvicorn / FastAPI logs and application logs merge into a single stream
with consistent formatting.
"""

import logging
import os
import structlog


def configure_logging(log_level: str = "INFO") -> None:
    """Configure structlog for structured console (dev) or JSON (prod) logging."""
    level = getattr(logging, log_level.upper(), logging.INFO)

    # Shared pre-chain processors (run before the final renderer)
    shared_processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
    ]

    is_dev = os.environ.get("APP_ENV", "development") == "development"

    if is_dev:
        # Human-readable coloured output for local development
        renderer = structlog.dev.ConsoleRenderer()
    else:
        # Machine-parseable JSON for production / Docker
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=shared_processors + [renderer],
        # Use stdlib logger factory so .name is always available
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Ensure stdlib root logger level matches
    logging.basicConfig(
        format="%(message)s",
        level=level,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """Return a bound structlog logger."""
    return structlog.get_logger(name)

