"""Module providing widgets for non-EEG numeric data in MoBI_View.

Displays one numeric stream in a PlotWidget with multiple channels.
"""

from typing import Dict, List

import pyqtgraph as pg
from PyQt6.QtWidgets import QVBoxLayout, QWidget

MAX_SAMPLES = 500


class SingleStreamNumericPlotWidget(QWidget):
    """Displays one numeric stream in a PlotWidget with multiple channels.

    The plot title displays the stream name.
    """

    def __init__(self, stream_name: str, parent: QWidget | None = None) -> None:
        """Initializes the widget for a single numeric stream.

        Args:
            stream_name: The name of the numeric stream.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._stream_name: str = stream_name
        self._layout: QVBoxLayout = QVBoxLayout()
        self.setLayout(self._layout)
        self._plot_widget: pg.PlotWidget = pg.PlotWidget()
        self._plot_widget.addLegend()
        self._plot_widget.showGrid(x=True, y=True)
        self._plot_widget.setLabel("bottom", "Samples")
        self._plot_widget.setLabel("left", "Value")
        self._layout.addWidget(self._plot_widget)
        self._plot_widget.getPlotItem().setTitle(self._stream_name, size="20pt")
        self._channel_data_items: Dict[str, pg.PlotDataItem] = {}
        self._buffers: Dict[str, List[float]] = {}

    def define_channel_color(self, index: int) -> tuple:
        """Defines a distinct color for a channel based on its index.

        Args:
            index: The 0-based index of the channel.

        Returns:
            A tuple (R, G, B) with values in [0, 255].
        """
        r, g, b = pg.intColor(index, hues=12).getRgb()[:3]
        return (r, g, b)

    def add_channel(self, channel_name: str) -> None:
        """Adds a new channel to the numeric plot.

        Args:
            channel_name: The full channel identifier (e.g., "Stream:F1").
        """
        if channel_name not in self._channel_data_items:
            index = len(self._channel_data_items)
            color_rgb = self.define_channel_color(index)
            pen = pg.mkPen(color=color_rgb, width=2)
            short_label: str = channel_name.split(":", 1)[-1]
            data_item: pg.PlotDataItem = self._plot_widget.plot(
                name=short_label, pen=pen, symbol=None
            )
            self._channel_data_items[channel_name] = data_item
            self._buffers[channel_name] = []

    def update_data(
        self, channel_name: str, sample_value: float, visible: bool
    ) -> None:
        """Appends a new sample to the channel buffer and updates the plot.

        Args:
            channel_name: The full channel identifier.
            sample_value: The new data sample.
            visible: Whether the channel should be visible.
        """
        if channel_name not in self._channel_data_items:
            self.add_channel(channel_name)
        data_item: pg.PlotDataItem = self._channel_data_items[channel_name]
        buffer_list: List[float] = self._buffers[channel_name]
        if not visible:
            data_item.hide()
            return
        data_item.show()
        buffer_list.append(sample_value)
        if len(buffer_list) > MAX_SAMPLES:
            buffer_list.pop(0)
        x_data = range(len(buffer_list))
        data_item.setData(x_data, buffer_list)


class MultiStreamNumericContainer(QWidget):
    """Container stacking multiple SingleStreamNumericPlotWidget widgets vertically."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initializes the container for multiple numeric streams.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._layout: QVBoxLayout = QVBoxLayout()
        self.setLayout(self._layout)
        self._stream_plots: Dict[str, SingleStreamNumericPlotWidget] = {}

    def update_data(
        self, stream_name: str, channel_name: str, sample_value: float, visible: bool
    ) -> None:
        """Updates data for a specific channel in a numeric stream.

        Args:
            stream_name: The name of the numeric stream.
            channel_name: The full channel identifier.
            sample_value: The new data sample.
            visible: Whether the channel should be visible.
        """
        if stream_name not in self._stream_plots:
            widget: SingleStreamNumericPlotWidget = SingleStreamNumericPlotWidget(
                stream_name
            )
            self._stream_plots[stream_name] = widget
            self._layout.addWidget(widget)
        self._stream_plots[stream_name].update_data(channel_name, sample_value, visible)
