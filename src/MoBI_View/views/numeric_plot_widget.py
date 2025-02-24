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

    Attributes:
        _stream_name: The name of the numeric stream (e.g. "GazeStream").
        _layout: The main QVBoxLayout for this widget.
        _plot_widget: The pyqtgraph PlotWidget used to display numeric signals.
        _channel_data_items: Maps channel names to PlotDataItem objects.
        _buffers: Maps channel names to lists of float samples.
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
        self._plot_widget.showGrid(x=True, y=True)
        self._plot_widget.getPlotItem().setTitle(
            self._stream_name, color="w", bold=True, size="20pt"
        )
        self._layout.addWidget(self._plot_widget)

        self._channel_data_items: Dict[str, pg.PlotDataItem] = {}
        self._buffers: Dict[str, List[float]] = {}

    def define_channel_color(self, index: int) -> tuple:
        """Defines a distinct color for a channel based on its index.

        Args:
            index: The 0-based index of the channel.

        Returns:
            A tuple (R, G, B) in [0, 255].
        """
        r, g, b = pg.intColor(index, hues=12).getRgb()[:3]
        return (r, g, b)

    def add_channel(self, chan_name: str) -> None:
        """Adds a new channel to the numeric plot.

        Args:
            chan_name: The full channel identifier (e.g. "Eyetracking:Gaze_X").
        """
        if chan_name in self._channel_data_items:
            return
        idx = len(self._channel_data_items)
        color_rgb = self.define_channel_color(idx)
        pen = pg.mkPen(color=color_rgb, width=2)
        short_label = chan_name.split(":", 1)[-1]

        data_item = self._plot_widget.plot(name=short_label, pen=pen, symbol=None)
        self._channel_data_items[chan_name] = data_item
        self._buffers[chan_name] = []

    def update_data(self, chan_name: str, sample_val: float, visible: bool) -> None:
        """Appends a new sample to the channel buffer and updates the plot.

        Args:
            chan_name: The full channel identifier.
            sample_val: The new data sample.
            visible: Whether the channel should be visible.
        """
        if chan_name not in self._channel_data_items:
            self.add_channel(chan_name)

        data_item = self._channel_data_items[chan_name]
        buf = self._buffers[chan_name]

        buf.append(sample_val)
        if len(buf) > MAX_SAMPLES:
            buf.pop(0)

        data_item.setVisible(visible)
        x_data = range(len(buf))
        data_item.setData(x_data, buf)


class MultiStreamNumericContainer(QWidget):
    """Container stacking multiple SingleStreamNumericPlotWidget widgets.

    Attributes:
        _layout: The main QVBoxLayout for this container widget.
        _stream_plots: Maps stream names to SingleStreamNumericPlotWidget.
    """

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
        self, stream_name: str, chan_name: str, sample_val: float, visible: bool
    ) -> None:
        """Updates data for a specific channel in a numeric stream.

        Args:
            stream_name: The name of the numeric stream.
            chan_name: The full channel identifier.
            sample_val: The new data sample.
            visible: Whether the channel should be visible.
        """
        if stream_name not in self._stream_plots:
            plot_widget = SingleStreamNumericPlotWidget(stream_name)
            self._stream_plots[stream_name] = plot_widget
            self._layout.addWidget(plot_widget)

        self._stream_plots[stream_name].update_data(chan_name, sample_val, visible)
