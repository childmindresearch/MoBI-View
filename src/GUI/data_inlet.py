"""Module for handling data inlet."""
import numpy as np
import pylsl
import pyqtgraph as pg
from config import BUFFER_SIZE, Y_MARGIN
from pyqtgraph.Qt import QtCore, QtWidgets


class DataInlet:
    """A DataInlet for pulling and plotting multiple channels."""

    def __init__(
        self, info: pylsl.StreamInfo, plot_item: pg.PlotItem
    ) -> None:
        """Initialize the DataInlet object.

        Args:
            info: The LSL stream info.
            plot_item: The plot item for displaying the data.
        """
        self.inlet = pylsl.StreamInlet(info)
        self.channel_names = self.get_channel_names(info)
        self.channel_count = len(self.channel_names)
        self.buffers = np.zeros((self.channel_count, BUFFER_SIZE))
        self.ptr = 0

        # Initialize plot curves with distinct colors
        self.curves = []
        for i in range(self.channel_count):
            color = pg.intColor(i, hues=self.channel_count)
            curve = pg.PlotCurveItem(pen=pg.mkPen(color=color))
            plot_item.addItem(curve)
            self.curves.append(curve)

        self.plot_item = plot_item

    def get_channel_names(self, info: pylsl.StreamInfo) -> list[str]:
        """Fetch channel names from LSL stream info metadata.

        Args:
            info: The LSL stream info.

        Returns:
            A list of channel names.
        """
        channel_names = []
        try:
            # Attempt to retrieve the metadata for channels
            channels_element = info.desc().child("channels")
            if channels_element:
                channel = channels_element.child("channel")
                count = 0  # To prevent infinite loops
                while channel and count < info.channel_count():
                    label = channel.child_value("label")
                    if label:
                        channel_names.append(label)
                    else:
                        channel_names.append(f"Channel {len(channel_names)+1}")
                    channel = channel.next_sibling("channel")
                    count += 1
        except Exception as e:
            print(f"Error extracting channel names: {e}")

        # If no channel names are found, fallback to default names
        if not channel_names:
            print("No channel names found in metadata, using default names.")
            channel_names = [f"Channel {i + 1}" for i in range(info.channel_count())]

        print("Retrieved channel names:", channel_names)
        return channel_names

    def toggle_channel_visibility(self, channel_name: str, visible: bool) -> None:
        """Toggle the visibility of a specific channel's plot curve.

        Args:
            channel_name (str): The name of the channel.
            visible (bool): Whether the channel should be visible.
        """
        if channel_name in self.channel_names:
            index = self.channel_names.index(channel_name)
            if 0 <= index < len(self.curves):
                try:
                    self.curves[index].setVisible(visible)
                    self.adjust_y_scale()
                except RuntimeError as e:
                    print(f"Error toggling visibility for {channel_name}: {e}")

    def pull_and_plot(self) -> None:
        """Pull data from the inlet and update the plot."""
        try:
            samples, timestamp = self.inlet.pull_sample(timeout=0.0)
            if samples and len(samples) == self.channel_count:
                self.buffers[:, :-1] = self.buffers[:, 1:]
                self.buffers[:, -1] = samples
                self.update_plot()
        except Exception as e:
            print(f"Error pulling sample: {e}")

    def update_plot(self) -> None:
        """Update the plot curves with new data and handle NaN values."""
        for i in range(self.channel_count):
            buffer = self.buffers[i]
            if np.isnan(buffer).any():
                valid_data = buffer[np.isfinite(buffer)]
                y_min, y_max = (
                    (np.min(valid_data), np.max(valid_data))
                    if valid_data.size > 0
                    else (-1, 1)
                )
            else:
                y_min, y_max = np.min(buffer), np.max(buffer)
            try:
                self.curves[i].setData(
                    np.arange(self.ptr - BUFFER_SIZE + 1, self.ptr + 1), buffer
                )
            except RuntimeError as e:
                print(f"Error updating curve {self.channel_names[i]}: {e}")
        # Adjust the Y-scale after updating plots
        self.adjust_y_scale()
        # Update the X-range to scroll with the data
        try:
            self.plot_item.setXRange(self.ptr - BUFFER_SIZE, self.ptr)
        except RuntimeError as e:
            print(f"Error setting X range: {e}")
        self.ptr += 1

    def adjust_y_scale(self) -> None:
        """Adjust the Y-scale of the plot based on the data."""
        overall_min = np.inf
        overall_max = -np.inf
        for i in range(self.channel_count):
            if self.curves[i].isVisible():
                buffer = self.buffers[i]
                if np.isnan(buffer).any():
                    valid_data = buffer[np.isfinite(buffer)]
                    y_min, y_max = (
                        (np.min(valid_data), np.max(valid_data))
                        if valid_data.size > 0
                        else (-1, 1)
                    )
                else:
                    y_min, y_max = np.min(buffer), np.max(buffer)
                overall_min = min(overall_min, y_min)
                overall_max = max(overall_max, y_max)
        if overall_min == np.inf or overall_max == -np.inf:
            # No visible channels or no data, set default Y-range
            overall_min, overall_max = -1, 1
        else:
            # Adjust the Y-range with a margin for better visibility
            y_range_min = overall_min - abs(overall_min) * Y_MARGIN
            y_range_max = overall_max + abs(overall_max) * Y_MARGIN
        try:
            self.plot_item.setYRange(y_range_min, y_range_max)
        except RuntimeError as e:
            print(f"Error adjusting Y-scale: {e}")
