"""Module for handling data inlet."""

import numpy as np
import pylsl
import pyqtgraph as pg
from config import BUFFER_SIZE, Y_MARGIN
from pyqtgraph.Qt import QtCore, QtWidgets


class DataInlet:
    """A DataInlet for pulling and plotting multiple channels."""

    def __init__(
        self, info: pylsl.StreamInfo, plot_item: pg.PlotItem, layout: QtWidgets.QVBoxLayout
    ) -> None:
        """Initialize the DataInlet object.

        Args:
            info: The LSL stream info.
            plot_item: The plot item for displaying the data.
            layout: The layout for adding UI components.
        """
        self.inlet = pylsl.StreamInlet(info)
        self.channel_names = self.get_channel_names(info)
        self.channel_count = len(self.channel_names)
        self.buffers = np.zeros((self.channel_count, BUFFER_SIZE))

        self.curves = [
            pg.PlotCurveItem(pen=pg.mkPen(color=(i, self.channel_count * 1.3)))
            for i in range(self.channel_count)
        ]
        for curve in self.curves:
            plot_item.addItem(curve)

        self.plot_item = plot_item
        self.ptr = 0

        self.text_widget = QtWidgets.QTextEdit()
        self.text_widget.setReadOnly(True)
        layout.addWidget(self.text_widget)

        self.channel_controls = []
        self.visible_channels = np.ones(self.channel_count, dtype=bool)
        self.setup_channel_controls(layout)

    def get_channel_names(self, info: pylsl.StreamInfo) -> list[str]:
        """Fetch channel names from LSL stream info metadata."""
        channel_names = []
        # Print out the stream's XML description for debugging purposes
        print("Stream Metadata XML:\n", info.as_xml())

        # Try to retrieve the metadata for channels
        ch = info.desc().child("channels").child("channel")
        
        while ch.name() and ch.child_value("label"):
            channel_names.append(ch.child_value("label"))
            ch = ch.next_sibling("channel")
        
        # If no channel names are found in metadata, fallback to default names
        if not channel_names:
            print("No channel names found in metadata, using default names.")
            channel_names = [f"Channel {i + 1}" for i in range(info.channel_count())]

        print("Retrieved channel names:", channel_names)
        return channel_names

    def setup_channel_controls(self, layout: QtWidgets.QVBoxLayout) -> None:
        """Setup checkboxes and labels for each channel."""
        for i in range(self.channel_count):
            hbox = QtWidgets.QHBoxLayout()
            checkbox = QtWidgets.QCheckBox(self.channel_names[i])
            checkbox.setChecked(True)
            checkbox.stateChanged.connect(
                lambda state, x=i: self.toggle_channel_visibility(x, state)  # Explicitly pass `i` to avoid late binding issue
            )
            label = QtWidgets.QLabel(f"{self.channel_names[i]}: 0.000")
            hbox.addWidget(checkbox)
            hbox.addWidget(label)
            layout.addLayout(hbox)
            self.channel_controls.append((checkbox, label))

    def toggle_channel_visibility(self, channel_index: int, state: int) -> None:
        """Toggle the visibility of the plot curve based on checkbox state."""
        self.curves[channel_index].setVisible(state == QtCore.Qt.Checked)
        self.visible_channels[channel_index] = state == QtCore.Qt.Checked
        self.adjust_y_scale()  # Adjust Y-scale based on the visibility of channels

    def pull_and_plot(self) -> None:
        """Pull data from the inlet and update the plot."""
        samples, timestamp = self.inlet.pull_sample(timeout=0.0)
        if samples and len(samples) == self.channel_count:
            self.buffers[:, :-1] = self.buffers[:, 1:]
            self.buffers[:, -1] = samples
            self.update_plot()
            self.update_text_widget()


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

            self.curves[i].setData(
                np.arange(self.ptr - BUFFER_SIZE + 1, self.ptr + 1), buffer
            )
        
        # Adjust the Y-scale after updating plots
        self.adjust_y_scale()

        # Update the X-range to scroll with the data
        self.plot_item.setXRange(self.ptr - BUFFER_SIZE + 50, self.ptr + 50)
        self.ptr += 1

    def adjust_y_scale(self) -> None:
        """Adjust the Y-scale of the plot based on the visible data."""
        overall_min = np.inf
        overall_max = -np.inf
        for i in range(self.channel_count):
            if self.visible_channels[i]:  # Only consider visible channels
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

        # Adjust the Y-range with a margin for better visibility
        y_range_min = overall_min - abs(overall_min) * Y_MARGIN
        y_range_max = overall_max + abs(overall_max) * Y_MARGIN
        self.plot_item.setYRange(y_range_min, y_range_max)

    def update_text_widget(self) -> None:
        """Update the labels next to checkboxes with the data for each channel."""
        self.text_widget.clear()
        for i in range(self.channel_count):
            if self.visible_channels[i]:  # Only display visible channels
                self.text_widget.append(f"{self.channel_names[i]}: {self.buffers[i, -1]:.3f}")
