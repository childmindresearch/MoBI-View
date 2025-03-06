"""Custom exceptions for MoBI View."""


class StreamLostError(Exception):
    """Exception raised when the stream source has been lost."""

    pass


class InvalidChannelFormatError(Exception):
    """Exception raised when the sample data type is invalid."""

    pass


class InvalidChannelCountError(Exception):
    """Exception raised when the channel count is invalid."""

    pass


class DuplicateChannelLabelError(Exception):
    """Exception raised when a duplicate channel name is added to the same stream."""

    pass
