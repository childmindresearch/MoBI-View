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
        STREAM_RESOLVE_WAIT_TIME: Time in seconds to wait for LSL stream discovery.
            LSL recommends 1.0s (default) or 2.0s for busy networks. Minimum 0.5s.
            Validation (positive, >= 0.5s) is performed in discover_and_create_inlets().
    """

    BUFFER_SIZE: int = 1000
    TIMER_INTERVAL: int = 50
    MAX_SAMPLES: int = 500
    EEG_OFFSET: int = 50
    STREAM_RESOLVE_WAIT_TIME: float = 1.0
