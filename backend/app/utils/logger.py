"""Logger configuration utilities."""
import logging
import os

_LOGGER_INITIALIZED = False


def configure_logging() -> None:
    global _LOGGER_INITIALIZED
    if _LOGGER_INITIALIZED:
        return
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=level,
        format="%(levelname)s | %(asctime)s | %(name)s | %(message)s",
    )
    _LOGGER_INITIALIZED = True


def get_logger(name: str) -> logging.Logger:
    configure_logging()
    return logging.getLogger(name)
