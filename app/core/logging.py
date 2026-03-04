# Logging configuration — sets up a single structured handler for the entire application.

import logging
import sys

from app.core.config import settings


def configure_logging() -> None:
    # Apply log level from settings; fall back to INFO if the value is unrecognised
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    # Stream to stdout so container orchestrators capture logs correctly
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    # Silence noisy third-party loggers
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    # Each module calls get_logger(__name__) to receive a named logger
    return logging.getLogger(name)
