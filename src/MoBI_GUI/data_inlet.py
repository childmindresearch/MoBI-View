"""Basic functions for MoBI_GUI DataInlet Class(Model)."""

from typing import Dict, List

import numpy as np
from pylsl import LostError, StreamInfo, StreamInlet
from PyQt5.QtCore import QObject

from MoBI_GUI.config import Config
from MoBI_GUI.exceptions import StreamLostError


class DataInlet(QObject):
    """DataInlet class responsible for acquiring data from LSL streams."""

    def __init__(self, info: StreamInfo) -> None:
        """Initializes the DataInlet instance.

        Args:
            info: Information about the LSL stream.
        """
        super().__init__()
        self.inlet = StreamInlet(info)
        self.channel_info: Dict[str, List[str]] = self.get_channel_information(info)
        self.channel_names: List[str] = self.channel_info.get("labels", [])
        self.channel_count: int = info.channel_count()
        self.buffers: np.ndarray = np.zeros((Config.BUFFER_SIZE, self.channel_count))
        self.ptr: int = 0

    def get_channel_information(self, info: StreamInfo) -> Dict[str, List[str]]:
        """Extracts channel information from the StreamInfo.

        Args:
            info: Information about the LSL stream.

        Returns:
            A dictionary containing channel information: names, types, units.
        """
        channel_labels = info.get_channel_labels()
        channel_types = info.get_channel_types()
        channel_units = info.get_channel_units()
        channel_info: Dict[str, List[str]] = {"labels": [], "types": [], "units": []}

        for i in range(info.channel_count()):
            channel_label = (
                channel_labels[i]
                if channel_labels and channel_labels[i]
                else f"Channel {i+1}"
            )
            channel_type = (
                channel_types[i] if channel_types and channel_types[i] else "unknown"
            )
            channel_unit = (
                channel_units[i] if channel_units and channel_units[i] else "unknown"
            )

            channel_info["labels"].append(channel_label)
            channel_info["types"].append(channel_type)
            channel_info["units"].append(channel_unit)

        return channel_info

    def pull_sample(self) -> None:
        """Pulls a data sample from the LSL stream and updates the buffer.

        Raises:
            StreamLostError: If the stream source has been lost,
            and LostError from pylsl is raised.
        """
        try:
            sample, _ = self.inlet.pull_sample(timeout=0.0)
            if sample:
                self.buffers[self.ptr % Config.BUFFER_SIZE] = sample
                self.ptr += 1
        except LostError:
            raise StreamLostError("Stream source has been lost.")
