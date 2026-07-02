"""
Centralized logging configuration for the trading bot.

All API requests, responses, and errors are written to a rotating log
file (logs/trading_bot.log) as well as to the console (INFO level and
above), so the user gets immediate feedback while a full audit trail
is kept on disk.
"""

import logging
import os
from logging.handlers import RotatingFileHandler

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
LOG_FILE = os.path.join(LOG_DIR, "trading_bot.log")


def setup_logger(name: str = "trading_bot", log_file: str = LOG_FILE, level: int = logging.DEBUG) -> logging.Logger:
    """
    Create and configure a logger with both a rotating file handler
    (captures everything, for the audit trail / deliverable log files)
    and a console handler (captures INFO+ only, to keep the terminal
    readable).
    """
    os.makedirs(LOG_DIR, exist_ok=True)

    logger = logging.getLogger(name)

    # Avoid attaching duplicate handlers if setup_logger() is called
    # more than once (e.g. imported in multiple modules / tests).
    if logger.handlers:
        return logger

    logger.setLevel(level)
    logger.propagate = False

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Rotating file handler: 5 files x 1MB, keeps logs bounded in size
    file_handler = RotatingFileHandler(log_file, maxBytes=1_000_000, backupCount=5, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
