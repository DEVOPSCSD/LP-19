"""
Logger Module
-------------
Provides application-wide structured logging for the Automatic File Organizer.
Records key events:
    - Application start
    - Directory scan
    - Files detected
    - Files successfully moved
    - Duplicate filename handling
    - Errors
    - Application completion
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Union

LOGGER_NAME = "file_organizer"


def setup_logger(
    log_file: Optional[Union[str, Path]] = None,
    level: int = logging.INFO,
) -> logging.Logger:
    """Configure and return the application logger.

    Sets up a formatted console handler and an optional file handler.
    Prevents adding duplicate handlers on multiple calls.

    Args:
        log_file: Optional path to log file (e.g. logs/organizer.log).
        level: Logging severity level (default logging.INFO).

    Returns:
        Configured logging.Logger instance.
    """
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level)
    logger.propagate = False

    # Clear existing handlers to avoid duplicate output during multiple runs/tests
    if logger.hasHandlers():
        logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 1. Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 2. File handler (if log_file path provided)
    if log_file is not None:
        file_path = Path(log_file)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(file_path, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger() -> logging.Logger:
    """Retrieve existing logger or create one with default console settings."""
    logger = logging.getLogger(LOGGER_NAME)
    if not logger.handlers:
        return setup_logger()
    return logger
