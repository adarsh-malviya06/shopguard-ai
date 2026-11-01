"""Logging configuration for ShopGuard AI."""

import logging
import sys
from pathlib import Path
from src.shopguard.config import settings


def setup_logger(name: str = "shopguard") -> logging.Logger:
    """Set up and return a configured logger instance."""
    logger = logging.getLogger(name)
    level = getattr(logging, settings.LOG_LEVEL, logging.INFO)
    logger.setLevel(level)

    # Avoid adding duplicate handlers if already configured
    if logger.handlers:
        return logger

    # Formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)
    logger.addHandler(console_handler)

    # File Handler
    settings.LOGS_DIR.mkdir(parents=True, exist_ok=True)
    file_path = settings.LOGS_DIR / "shopguard.log"
    file_handler = logging.FileHandler(file_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)
    logger.addHandler(file_handler)

    return logger


logger = setup_logger()
