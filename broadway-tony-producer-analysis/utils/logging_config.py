"""
Logging configuration for the Broadway analysis pipeline.

Provides structured, consistent logging across all modules.
"""

import logging
import sys
from pathlib import Path


def setup_logger(name: str, level: int = logging.INFO, log_file: Path = None) -> logging.Logger:
    """
    Set up a logger with consistent formatting.

    Parameters
    ----------
    name : str
        Name of the logger (typically __name__ from calling module)
    level : int
        Logging level (default: logging.INFO)
    log_file : Path, optional
        If provided, also log to this file

    Returns
    -------
    logging.Logger
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    # Create formatter
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (optional)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
