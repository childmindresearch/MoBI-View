"""Configuration module for MoBI_View application.

This module contains the Config class.
"""


class Config:
    """Configuration class holding application-wide settings.

    Attributes:
        BUFFER_SIZE: Size of the buffer for storing data samples.
        TIMER_INTERVAL: Timer interval in milliseconds for data acquisition.
    """

    BUFFER_SIZE: int = 1000
    TIMER_INTERVAL: int = 50
    MAX_SAMPLES: int = 500
