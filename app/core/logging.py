import logging
import sys

import structlog


def configure_logging(level: str = "INFO", log_format: str = "json") -> None:
    """Set up structlog so every log line is a structured event.

    `merge_contextvars` is the key processor: anything bound with
    `structlog.contextvars.bind_contextvars(trace_id=...)` (done per request by the
    middleware) is automatically added to every log line emitted while handling it.
    """
    renderer = (
        structlog.processors.JSONRenderer()
        if log_format == "json"
        else structlog.dev.ConsoleRenderer()
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelNamesMapping()[level]),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
