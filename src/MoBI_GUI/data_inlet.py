# src/GUI/data_inlet.py

"""Basic functions for MoBI_GUI DataInlet Class(Model)."""

from typing import List
from xml.etree.ElementTree import Element

import numpy as np
import pyqtgraph as pg
from pylsl import StreamInfo, StreamInlet
from PyQt5.QtCore import QObject, pyqtSignal

from .config import Config, get_logger

logger = get_logger(__name__)


class DataInlet(QObject):
    """DataInlet class responsible for acquiring data from LSL streams.

    Attributes:
        data_updated (pyqtSignal): Signal emitted when new data is acquired.
    """

    data_updated = pyqtSignal(str, dict)

    def __init__(self, info: StreamInfo, plot_item: pg.PlotItem) -> None:
        """Initializes the DataInlet instance.

        Args:
            info (StreamInfo): Information about the LSL stream.
            plot_item (pg.PlotItem): Plot item to visualize data.
        """
        super().__init__()
        self.inlet: StreamInlet = StreamInlet(info)
        self.channel_names: List[str] = self.get_channel_names(info)
        self.channel_count: int = len(self.channel_names)
        self.buffers: np.ndarray = np.zeros((Config.BUFFER_SIZE, self.channel_count))
        self.ptr: int = 0
        self.plot_item: pg.PlotItem = plot_item
        self.curves: List[pg.PlotCurveItem] = []
        logger.debug(
            (
                f"Initialized DataInlet for stream: {info.name()} "
                f"with channels: {self.channel_names}"
            )
        )

    def get_channel_names(self, info: StreamInfo) -> List[str]:
        """Extracts channel names from the StreamInfo.

        Args:
            info (StreamInfo): Information about the LSL stream.

        Returns:
            List[str]: List of channel names.
        """
        try:
            desc = info.desc()
            if not isinstance(desc, Element):
                logger.error("Expected XML Element from StreamInfo.desc()")
                return [f"Channel {i+1}" for i in range(info.channel_count())]

            channels = desc.find("channels")
            if channels is None:
                logger.warning(
                    "No 'channels' element found in StreamInfo. "
                    "Using default channel names."
                )
                return [f"Channel {i+1}" for i in range(info.channel_count())]

            channel_names = []
            for channel in channels.findall("channel"):
                label = channel.findtext("label")
                if label:
                    channel_names.append(label)
                else:
                    channel_names.append(f"Channel {len(channel_names) + 1}")

            logger.debug(f"Extracted channel names: {channel_names}")
            return channel_names
        except Exception as e:
            logger.error(f"Error extracting channel names: {e}")
            return [f"Channel {i+1}" for i in range(info.channel_count())]

    def toggle_channel_visibility(self, channel_name: str, visible: bool) -> None:
        """Toggles the visibility of a specific channel's plot.

        Args:
            channel_name (str): Name of the channel.
            visible (bool): Visibility state.
        """
        try:
            index = self.channel_names.index(channel_name)
            self.plot_item.showCurve(index, visible)
            logger.info(f"Toggled visibility for {channel_name} to {visible}")
        except ValueError:
            logger.warning(f"Channel {channel_name} not found.")

    def pull_sample(self) -> None:
        """Pulls a data sample from the LSL stream and updates the buffer.

        Emits a data_updated signal with the new data.
        """
        try:
            sample, timestamp = self.inlet.pull_sample(timeout=0.0)
            if sample:
                self.buffers[self.ptr % Config.BUFFER_SIZE] = sample
                data = {
                    name: self.buffers[:, i].tolist()
                    for i, name in enumerate(self.channel_names)
                }
                self.data_updated.emit(self.inlet.info().name(), data)
                self.ptr += 1
                logger.debug(
                    f"Pulled sample {self.ptr} from stream {self.inlet.info().name()}"
                )
        except Exception as e:
            logger.error(f"Error pulling sample: {e}")

    def update_plot(self) -> None:
        """Updates the plot with new data from the buffer."""
        try:
            self.plot_item.clear()
            for i, channel in enumerate(self.channel_names):
                if self.plot_item.isVisible(i):
                    curve = self.plot_item.plot(
                        self.buffers[:, i], pen=pg.intColor(i), name=channel
                    )
                    self.curves.append(curve)
            logger.debug("Plot updated with new data.")
        except Exception as e:
            logger.error(f"Error updating plot: {e}")

    def adjust_y_scale(self) -> None:
        """Adjusts the Y-axis scale based on the current data buffer."""
        try:
            data_min = np.min(self.buffers)
            data_max = np.max(self.buffers)
            margin = Config.Y_MARGIN * (data_max - data_min)
            self.plot_item.setYRange(data_min - margin, data_max + margin)
            logger.debug("Y-axis scale adjusted.")
        except Exception as e:
            logger.error(f"Error adjusting Y scale: {e}")
