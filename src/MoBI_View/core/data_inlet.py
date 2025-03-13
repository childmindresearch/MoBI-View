"""Module providing the DataInlet class for MoBI_View.

The DataInlet class is responsible for acquiring and buffering data from LSL streams.
"""

from typing import Dict, List

import numpy as np
from pylsl.info import StreamInfo
from pylsl.inlet import StreamInlet
from pylsl.util import LostError
from PyQt6 import QtCore

from MoBI_View.core import config, exceptions


class DataInlet(QtCore.QObject):
    """Handles data acquisition from LSL streams.

    Attributes:
        inlet: The LSL stream inlet for acquiring data.
        stream_name: The name of the LSL stream.
        stream_type: The content type of the LSL stream (e.g., EEG, Gaze).
        channel_info: Information about channels, including labels, types, and units.
        channel_count: The number of channels in the LSL stream.
        channel_format: The format (data type) of the channel data.
        buffers: Buffer to store incoming samples, initialized to zeros.
        ptr: Pointer to the current index in the buffer.
    """

    def __init__(self, partial_info: StreamInfo) -> None:
        """Initializes the DataInlet instance and performs initial validation.

        Sets up the LSL stream inlet, extracts channel information, initializes the
        buffer for storing incoming data samples, and validates the channel count
        and channel format to ensure compatibility.

        Args:
            partial_info: The partial StreamInfo from resolve_streams().
            Per pylsl, inlet.info() must be called to get the full metadata.

        Raises:
            InvalidChannelCountError: If the stream has no channels.
            InvalidChannelFormatError: If the sample data type is invalid.
        """
        super().__init__()
        self.inlet = StreamInlet(partial_info)
        info: StreamInfo = self.inlet.info()

        self.stream_name: str = info.name()
        self.stream_type: str = info.type()
        self.channel_info: Dict[str, List[str]] = self.get_channel_information(info)
        self.channel_count: int = info.channel_count()
        self.channel_format: int = info.channel_format()
        self.buffers: np.ndarray = np.zeros(
            (config.Config.BUFFER_SIZE, self.channel_count)
        )
        self.ptr: int = 0

        if self.channel_count <= 0:
            raise exceptions.InvalidChannelCountError(
                "Unable to plot data without channels."
            )

        valid_channel_formats = {1, 2, 4, 5, 6}
        if info.channel_format() not in valid_channel_formats:
            raise exceptions.InvalidChannelFormatError(
                "Unable to plot non-numeric data."
            )

    def get_channel_information(self, info: StreamInfo) -> Dict[str, List[str]]:
        """Extracts channel information from the StreamInfo.

        Gathers channel-specific information from the LSL StreamInfo object, such as
        channel labels, types, and units. If any of this information is missing or
        contains `None` values, default values are used.

        Args:
            info: Information about the LSL stream.

        Returns:
            A dictionary containing channel information with keys 'labels',
            'types', and 'units'. If metadata is missing, default values are used.
        """
        channel_labels = info.get_channel_labels() or []
        channel_types = info.get_channel_types() or []
        channel_units = info.get_channel_units() or []

        channel_count = info.channel_count()
        channel_info: Dict[str, List[str]] = {"labels": [], "types": [], "units": []}

        channel_info["labels"] = [
            channel_labels[i]
            if i < len(channel_labels) and channel_labels[i] is not None
            else f"Channel {i + 1}"
            for i in range(channel_count)
        ]
        channel_info["types"] = [
            channel_types[i]
            if i < len(channel_types) and channel_types[i] is not None
            else "unknown"
            for i in range(channel_count)
        ]
        channel_info["units"] = [
            channel_units[i]
            if i < len(channel_units) and channel_units[i] is not None
            else "unknown"
            for i in range(channel_count)
        ]

        return channel_info

    def pull_sample(self) -> None:
        """Pulls a data sample from the LSL stream and updates the buffer.

        Retrieves a sample from the LSL stream inlet and stores it in the buffer.
        If the stream is lost during the operation, a StreamLostError is raised.

        Raises:
            StreamLostError: If the stream source has been lost.
        """
        try:
            sample, _ = self.inlet.pull_sample(timeout=0.0)
            if sample:
                self.buffers[self.ptr % config.Config.BUFFER_SIZE] = sample
                self.ptr += 1
        except LostError:
            raise exceptions.StreamLostError("Stream source has been lost.")
