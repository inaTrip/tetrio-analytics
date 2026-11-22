"""Logging setup shared by every pipeline module.

All modules log under the "pipeline" logger, so every message goes to the
console and to logs/pipeline.log with the same format. The log file is
what the monitoring/alerting step will read later.
"""
import logging
import sys

from src.settings import LOG_DIR

_ROOT_NAME = "pipeline"
_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def _configure_root() -> None:
    """Attach the console and file handlers once to the parent logger."""
    root = logging.getLogger(_ROOT_NAME)
    if root.handlers:            # already configured: avoid duplicated lines
        return
    root.setLevel(logging.INFO)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter(_FORMAT)
    handlers = (
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_DIR / "pipeline.log", encoding="utf-8"),
    )
    for handler in handlers:
        handler.setFormatter(formatter)
        root.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    """Return a child logger, e.g. get_logger("ingestion.tetrio")."""
    _configure_root()
    return logging.getLogger(f"{_ROOT_NAME}.{name}")
