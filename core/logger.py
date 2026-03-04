"""
Application-wide logging configuration.
"""
import logging
import sys

from core.config import get_settings


def setup_logging() -> None:
    settings = get_settings()
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    logging.basicConfig(
        level=level,
        format=fmt,
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    # Quieten noisy third-party loggers
    for noisy in ("httpcore", "httpx", "openai", "twilio"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
