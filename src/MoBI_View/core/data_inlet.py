"""Module providing the DataInlet class for MoBI_View.

The DataInlet class is responsible for acquiring and buffering data from LSL streams.
"""

from typing import Any, Dict, List, Tuple

import numpy as np
from pylsl import info as pylsl_info
from pylsl import inlet as pylsl_inlet
from pylsl import util as pylsl_util

from MoBI_View.core import config, exceptions


class DataInlet:
    """Stores metadata and buffered samples for a single LSL stream.

    The DataInlet validates stream configuration, normalizes channel metadata,
    and keeps a buffer of recent samples for downstream consumers.

    Attributes:
        inlet: The LSL stream inlet for acquiring data.
        stream_name: The name of the LSL stream.
        stream_type: The content type of the LSL stream (e.g., EEG, Gaze).
        source_id: The source ID of the LSL stream (unique identifier).
        channel_info: Information about channels, including labels, types, and units.
        channel_count: The number of channels in the LSL stream.
        channel_format: The format (data type) of the channel data.
        buffers: Buffer to store incoming samples, initialized to zeros.
        timestamps: Buffer of LSL timestamps aligned with `buffers`.
        ptr: Pointer to the current index in the buffer.
    """

    def __init__(self, partial_info: pylsl_info.StreamInfo) -> None:
        """Initializes the DataInlet instance and performs initial validation.

        Sets up the LSL stream inlet, extracts channel information, initializes
        the buffer for storing incoming data samples, and validates the channel
        count and channel format to ensure compatibility.

        Args:
            partial_info: The partial StreamInfo from resolve_streams().
            Per pylsl, inlet.info() must be called to get the full metadata.

        Raises:
            InvalidChannelCountError: If the stream has no channels.
            InvalidChannelFormatError: If the sample data type is invalid.
        """
        self.inlet = pylsl_inlet.StreamInlet(partial_info)
        info: pylsl_info.StreamInfo = self.inlet.info()

        self.stream_name: str = info.name()
        self.stream_type: str = info.type()
        self.source_id: str = info.source_id()
        self.channel_info: Dict[str, List[str]] = self.get_channel_information(info)
        self.channel_count: int = info.channel_count()
        self.channel_format: int = info.channel_format()
        buffer_shape = (config.Config.BUFFER_SIZE, self.channel_count)
        if self.channel_format == 3:
            self.buffers = np.full(buffer_shape, "", dtype=object)
        else:
            self.buffers = np.zeros(buffer_shape)
        self.timestamps = np.zeros(config.Config.BUFFER_SIZE)
        self.ptr: int = 0

        if self.channel_count <= 0:
            raise exceptions.InvalidChannelCountError(
                "Unable to plot data without channels."
            )

        valid_channel_formats = {1, 2, 3, 4, 5, 6}
        if info.channel_format() not in valid_channel_formats:
            raise exceptions.InvalidChannelFormatError(
                "Unable to process unsupported channel data."
            )

    def get_channel_information(
        self, info: pylsl_info.StreamInfo
    ) -> Dict[str, List[str]]:
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
        """Pulls a single data sample from the LSL stream and updates the buffer.

        Retrieves a sample from the LSL stream inlet and stores it in the buffer.
        If the stream is lost during the operation, a StreamLostError is raised.

        Raises:
            StreamLostError: If the stream source has been lost.
        """
        self.pull_chunk(max_samples=1)

    def pull_chunk(
        self, max_samples: int = config.Config.MAX_SAMPLES_PER_POLL
    ) -> Tuple[List[List[Any]], List[float]]:
        """Drains buffered samples from the LSL stream without blocking.

        Samples are pulled until the inlet reports no further data or
        `max_samples` is reached, which keeps fast streams from falling behind
        real time while bounding the work done in a single poll.

        Args:
            max_samples: Maximum number of samples to pull in this call.

        Returns:
            A tuple of `(samples, timestamps)` for the samples pulled in this
            call, where `samples` holds one list of channel values per sample.

        Raises:
            StreamLostError: If the stream source has been lost.
        """
        samples: List[List[Any]] = []
        timestamps: List[float] = []
        try:
            for _ in range(max_samples):
                sample, timestamp = self.inlet.pull_sample(timeout=0.0)
                if not sample:
                    break
                index = self.ptr % config.Config.BUFFER_SIZE
                self.buffers[index] = sample
                self.timestamps[index] = timestamp
                self.ptr += 1
                samples.append(list(sample))
                timestamps.append(float(timestamp))
        except pylsl_util.LostError:
            raise exceptions.StreamLostError("Stream source has been lost.")
        return samples, timestamps
