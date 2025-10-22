"""Configuration module for MoBI_View application.

This module contains the Config class.
"""


class Config:
    """Configuration class holding application-wide settings.

    Attributes:
        BUFFER_SIZE: Size of the buffer for storing data samples.
        TIMER_INTERVAL: Timer interval in milliseconds for data polling.
        MAX_SAMPLES: Maximum number of samples to display (for numeric and EEG
            widgets).
        EEG_OFFSET: Vertical offset between EEG channels in the plot (for EEG
            widgets).
        HTTP_HOST: Default host for the HTTP server in web mode.
        HTTP_PORT: Default port for the HTTP server in web mode.
        WS_HOST: Default host for the WebSocket server in web mode.
        WS_PORT: Default port for the WebSocket server in web mode.
        POLL_INTERVAL: Interval in seconds for polling LSL samples in web mode.
        RESOLVE_INTERVAL: Interval in seconds for discovering new LSL streams in
            web mode.
        RESOLVE_WAIT: Wait time in seconds for LSL stream resolution in web
            mode.
    """

    BUFFER_SIZE: int = 1000
    TIMER_INTERVAL: int = 5
    MAX_SAMPLES: int = 1000
    EEG_OFFSET: int = 200
    HTTP_HOST: str = "0.0.0.0"
    HTTP_PORT: int = 8000
    WS_HOST: str = "0.0.0.0"
    WS_PORT: int = 8765
    POLL_INTERVAL: float = 0.002
    RESOLVE_INTERVAL: float = 5.0
    RESOLVE_WAIT: float = 0.1
