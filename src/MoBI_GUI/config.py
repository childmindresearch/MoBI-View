"""Configuration module for MoBI_GUI application.

This module contains the Config class and a function to set up loggers.
"""

import logging


class Config:
    """Configuration class holding application-wide settings."""

    BUFFER_SIZE: int = 1000
    Y_MARGIN: float = 0.1
    TIMER_INTERVAL: int = 50  # in milliseconds
    LOG_FILE: str = "app.log"
    LOG_LEVEL: str = "DEBUG"  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL


def get_logger(name: str) -> logging.Logger:
    """Sets up and returns a logger with the specified name.

    Args:
        name (str): The name of the logger.

    Returns:
        logging.Logger: Configured logger instance.
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, Config.LOG_LEVEL.upper(), logging.DEBUG))

    # Prevent adding multiple handlers to the logger in interactive environments
    if not logger.handlers:
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(
            getattr(logging, Config.LOG_LEVEL.upper(), logging.DEBUG)
        )
        console_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        # File handler
        file_handler = logging.FileHandler(Config.LOG_FILE)
        file_handler.setLevel(getattr(logging, Config.LOG_LEVEL.upper(), logging.DEBUG))
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger
