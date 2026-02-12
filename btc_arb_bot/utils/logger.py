"""Structured logger setup for console and file sinks."""

from __future__ import annotations

import json
import logging
from logging import Logger
from pathlib import Path
from typing import Any


class JsonFormatter(logging.Formatter):
    """Simple JSON formatter to support machine-readable logs."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def setup_logger(log_file: str, level: int = logging.INFO) -> Logger:
    """Configure and return the application logger."""

    logger = logging.getLogger("btc_arb_bot")
    logger.setLevel(level)
    logger.handlers.clear()

    Path(log_file).parent.mkdir(parents=True, exist_ok=True)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))

    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(JsonFormatter())

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    logger.propagate = False

    return logger
