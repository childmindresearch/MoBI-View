"""Custom exceptions for MoBI GUI."""


class StreamLostError(Exception):
    """Exception raised when the stream source has been lost."""

    pass


class InvalidChannelFormatError(Exception):
    """Exception raised when the sample data type is invalid."""

    pass


class InvalidChannelCountError(Exception):
    """Exception raised when the channel count is invalid."""

    pass
