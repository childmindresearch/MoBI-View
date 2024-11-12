"""Module providing the DataInlet class for MoBI_GUI.

The DataInlet class is responsible for acquiring and buffering data from LSL streams.
"""

from typing import Dict, List

import numpy as np
from pylsl import LostError, StreamInfo, StreamInlet
from PyQt5.QtCore import QObject

from MoBI_GUI.config import Config
from MoBI_GUI.exceptions import (
    InvalidChannelCountError,
    InvalidSampleError,
    StreamLostError,
)


class DataInlet(QObject):
    """Handles data acquisition from LSL streams.

    Attributes:
        inlet: The LSL stream inlet for acquiring data.
        channel_info: Information about channels, including labels, types, and units.
        channel_count: The number of channels in the LSL stream.
        buffers: Buffer to store incoming samples, initialized to zeros.
        ptr: Pointer to the current index in the buffer.
    """

    def __init__(self, info: StreamInfo) -> None:
        """Initializes the DataInlet instance and performs initial validation.

        Sets up the LSL stream inlet, extracts channel information, initializes the
        buffer for storing incoming data samples, and validates the channel count
        and channel format to ensure compatibility.

        Args:
            info: Information about the LSL stream.

        Raises:
            InvalidChannelCountError: If the stream has no channels.
            InvalidSampleError: If the sample data type is invalid.
        """
        super().__init__()
        self.inlet = StreamInlet(info)
        self.stream_name: str = info.name()
        self.stream_type: str = info.type() 
        self.channel_info: Dict[str, List[str]] = self.get_channel_information(info)
        self.channel_count: int = info.channel_count()

        if self.channel_count <= 0:
            raise InvalidChannelCountError("Unable to plot data without channels.")

        self.buffers: np.ndarray = np.zeros((Config.BUFFER_SIZE, self.channel_count))
        self.ptr: int = 0

        numeric_formats = {
            1,  # cf_float32
            2,  # cf_double64
            4,  # cf_int32
            5,  # cf_int16
            6,  # cf_int8
            7,  # cf_int64
        }
        if info.channel_format() not in numeric_formats:
            raise InvalidSampleError("Unable to plot non-numeric data.")

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
            else f"Channel {i+1}"
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
                self.buffers[self.ptr % Config.BUFFER_SIZE] = sample
                self.ptr += 1
        except LostError:
            raise StreamLostError("Stream source has been lost.")
