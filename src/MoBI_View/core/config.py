"""Configuration module for MoBI_View application.

This module contains the Config class.
"""


class Config:
    """Configuration class holding application-wide settings.

    Attributes:
        BUFFER_SIZE: Size of the buffer for storing data samples.
        TIMER_INTERVAL: Timer interval in milliseconds for data acquisition.
        MAX_SAMPLES: Maximum number of samples to display (for numeric and EEG widgets).
        EEG_OFFSET: Vertical offset between EEG channels in the plot (for EEG widgets).
    """

    BUFFER_SIZE: int = 1000
    TIMER_INTERVAL: int = 50
    MAX_SAMPLES: int = 500
    EEG_OFFSET: int = 50
