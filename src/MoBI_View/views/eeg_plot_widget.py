"""Module providing widgets for EEG data visualization in MoBI_View.

Displays EEG data with each channel in its own dedicated horizontal layout.
"""

from typing import Dict, List

import pyqtgraph as pg
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

MAX_SAMPLES = 500


class EEGPlotWidget(QWidget):
    """Displays EEG data with each channel shown in a separate plot area."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initializes the EEGPlotWidget.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._layout: QVBoxLayout = QVBoxLayout()
        self.setLayout(self._layout)
        self._channel_layouts: Dict[str, QHBoxLayout] = {}
        self._channel_plotwidgets: Dict[str, pg.PlotWidget] = {}
        self._channel_data_items: Dict[str, pg.PlotDataItem] = {}
        self._buffers: Dict[str, List[float]] = {}

    def add_channel(self, channel_name: str) -> None:
        """Adds a new channel layout with its label and plot.

        Args:
            channel_name: The full channel identifier (e.g., "EEGStream:Fz").
        """
        if channel_name in self._channel_layouts:
            return
        row_layout: QHBoxLayout = QHBoxLayout()
        label: QLabel = QLabel(channel_name.split(":", 1)[-1])
        label.setFixedWidth(30)
        row_layout.addWidget(label)
        plot_widget: pg.PlotWidget = pg.PlotWidget()
        plot_widget.showGrid(x=False, y=True)
        plot_widget.setLabel("left", "µV")
        data_item: pg.PlotDataItem = plot_widget.plot(
            pen=pg.mkPen(width=1, color="w"), symbol=None
        )
        row_layout.addWidget(plot_widget)
        self._layout.addLayout(row_layout)
        self._channel_layouts[channel_name] = row_layout
        self._channel_plotwidgets[channel_name] = plot_widget
        self._channel_data_items[channel_name] = data_item
        self._buffers[channel_name] = []

    def update_data(
        self, channel_name: str, sample_value: float, visible: bool
    ) -> None:
        """Appends a new sample to the channel buffer and updates its plot.

        Args:
            channel_name: The full channel identifier.
            sample_value: The new data sample.
            visible: Whether the channel is visible.
        """
        if channel_name not in self._channel_layouts:
            self.add_channel(channel_name)
        plot_widget: pg.PlotWidget = self._channel_plotwidgets[channel_name]
        data_item: pg.PlotDataItem = self._channel_data_items[channel_name]
        buffer_list: List[float] = self._buffers[channel_name]
        if not visible:
            plot_widget.hide()
            return
        plot_widget.show()
        buffer_list.append(sample_value)
        if len(buffer_list) > MAX_SAMPLES:
            buffer_list.pop(0)
        x_data = range(len(buffer_list))
        data_item.setData(x_data, buffer_list)
