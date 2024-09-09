"""Module for handling data inlet."""

from typing import List

import numpy as np
import pylsl
import pyqtgraph as pg  # For plotting
from config import BUFFER_SIZE, Y_MARGIN
from PyQt5.QtCore import Qt  # For Qt constants like `Qt.Checked`
from PyQt5.QtWidgets import QCheckBox, QHBoxLayout, QLabel  # For creating GUI elements


class DataInlet:
    """A DataInlet for pulling and plotting multiple channels."""

    def __init__(
        self, info: pylsl.StreamInfo, plot_item: pg.PlotItem, layout: QHBoxLayout
    ) -> None:
        """Initialize the DataInlet object.

        Args:
            info: The LSL stream info.
            plot_item: The plot item for displaying the data.
            layout: The layout for the channel controls.
        """
        self.inlet = pylsl.StreamInlet(info)
        self.channel_names = self.get_channel_names(info)
        self.channel_count = len(self.channel_names) - 1  # Exclude the first channel
        self.buffers = np.zeros((self.channel_count, BUFFER_SIZE))  # Preallocate buffer
        self.curves = [
            pg.PlotCurveItem(pen=pg.mkPen(color=(i, self.channel_count * 1.3)))
            for i in range(self.channel_count)
        ]
        for curve in self.curves:
            plot_item.addItem(curve)
        self.plot_item = plot_item
        self.ptr = 0  # Pointer to track the X-axis position

        # Setup UI components for channel controls
        self.channel_controls: list[tuple[QCheckBox, QLabel]] = []
        self.setup_channel_controls(layout)

    def get_channel_names(self, info: pylsl.StreamInfo) -> List[str]:
        """Fetch channel names from LSL stream info metadata."""
        channel_names = []
        ch = info.desc().child("channels").child("channel")
        while ch.name():
            channel_names.append(ch.child_value("label"))
            ch = ch.next_sibling("channel")
        return channel_names

    def setup_channel_controls(self, layout: QHBoxLayout) -> None:
        """Setup checkboxes and labels for each channel."""
        for i in range(self.channel_count):
            hbox = QHBoxLayout()
            checkbox = QCheckBox(self.channel_names[i + 1])
            checkbox.setChecked(True)
            checkbox.stateChanged.connect(
                lambda state, x=i: self.toggle_channel_visibility(x, state)
            )
            label = QLabel(f"{self.channel_names[i + 1]}: 0.000")
            hbox.addWidget(checkbox)
            hbox.addWidget(label)
            layout.addLayout(hbox)
            self.channel_controls.append((checkbox, label))

    def toggle_channel_visibility(self, channel_index: int, state: int) -> None:
        """Toggle the visibility of the plot curve based on checkbox state."""
        self.curves[channel_index].setVisible(state == Qt.Checked)

    def pull_and_plot(self) -> None:
        """Pull data from the inlet and update the plot."""
        samples, timestamp = self.inlet.pull_sample(timeout=0.0)
        if samples:
            # Roll the buffer and append the new sample for each channel (no 1st)
            self.buffers[:, :-1] = self.buffers[:, 1:]
            self.buffers[:, -1] = samples[1:]  # Skip the first channel

            # Handle NaN values and update plot for each channel
            overall_min, overall_max = self.update_plot()
            self.update_text_widget()

    def update_plot(self) -> None:
        """Update the plot curves with new data and handle NaN values."""
        overall_min = np.inf
        overall_max = -np.inf
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

            self.curves[i].setData(
                np.arange(self.ptr - BUFFER_SIZE + 1, self.ptr + 1), buffer
            )
            overall_min = min(overall_min, y_min)
            overall_max = max(overall_max, y_max)

        # Adjust the Y-range with a margin for better visibility
        y_range_min = overall_min - abs(overall_min) * Y_MARGIN
        y_range_max = overall_max + abs(overall_max) * Y_MARGIN
        self.plot_item.setYRange(y_range_min, y_range_max)
        # Update the X-range to scroll with the data
        self.plot_item.setXRange(self.ptr - BUFFER_SIZE + 50, self.ptr + 50)
        self.ptr += 1

    def update_text_widget(self) -> None:
        """Update the labels next to checkboxes with the data for each channel."""
        for i, (checkbox, label) in enumerate(self.channel_controls):
            if checkbox.isChecked():
                label.setText(f"{self.channel_names[i + 1]}: {self.buffers[i, -1]:.3f}")
