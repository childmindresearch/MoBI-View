"""Configuration module for MoBI_GUI application.

This module contains the Config class and a function to set up loggers(soon).
"""


class Config:
    """Configuration class holding application-wide settings."""

    BUFFER_SIZE: int = 1000
    Y_MARGIN: float = 0.1
    TIMER_INTERVAL: int = 50  # in milliseconds
