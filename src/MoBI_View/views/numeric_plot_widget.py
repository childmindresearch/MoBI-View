"""Module providing widgets for non-EEG numeric data in MoBI_View.

Displays one numeric stream in a PlotWidget with multiple channels.
"""

from typing import Dict, List

import pyqtgraph as pg
from PyQt6 import QtWidgets

from MoBI_View.core import config, exceptions


class SingleStreamNumericPlotWidget(QtWidgets.QWidget):
    """Displays one numeric stream in a PlotWidget with multiple channels.

    The plot title displays the stream name.

    Attributes:
        _stream_name: The name of the numeric stream (e.g. "GazeStream").
        _layout: The main QtWidgets.QVBoxLayout that arranges and contains the plot
            widget vertically.
        _plot_widget: The pyqtgraph PlotWidget used to display numeric signals.
        _channel_data_items: Maps channel names to PlotDataItem objects.
        _buffers: Maps channel names to lists of float samples.
    """

    def __init__(
        self, stream_name: str, parent: QtWidgets.QWidget | None = None
    ) -> None:
        """Initializes the widget for a single numeric stream.

        Args:
            stream_name: The name of the numeric stream.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._stream_name: str = stream_name
        self._layout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout()
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
        r, g, b = pg.intColor(index, values=3, hues=7).getRgb()[:3]
        return (r, g, b)

    def add_channel(self, channel_name: str) -> None:
        """Adds a new channel to the numeric plot.

        Args:
            channel_name: The fully qualified channel identifier
                (e.g. "Eyetracking:Gaze_X").

        Raises:
            DuplicateChannelLabelError: If a duplicate channel is added to the stream.
        """
        if channel_name in self._channel_data_items:
            raise exceptions.DuplicateChannelLabelError(
                "Unable to add a duplicate channel label under the same stream."
            )
        idx = len(self._channel_data_items)
        color_rgb = self.define_channel_color(idx)
        pen = pg.mkPen(color=color_rgb, width=2)
        short_label = channel_name.split(":", 1)[-1]

        data_item = self._plot_widget.plot(name=short_label, pen=pen, symbol=None)
        self._channel_data_items[channel_name] = data_item
        self._buffers[channel_name] = []

    def update_data(
        self,
        channel_name: str,
        sample_val: float,
        visible: bool,
        max_samples: int = config.Config.MAX_SAMPLES,
    ) -> None:
        """Appends a new sample to the channel buffer and updates the plot.

        Creates the channel if it does not exist yet (lazy initialization).
        Controls the visibility of the channel based on the `visible` parameter.

        Args:
            channel_name: The fully qualified channel identifier
                (e.g. "Eyetracking:Gaze_X").
            sample_val: The new data sample.
            visible: Whether the channel should be visible.
            max_samples: The maximum number of samples to keep in the buffer.
        """
        if channel_name not in self._channel_data_items:
            self.add_channel(channel_name)

        self._buffers[channel_name].append(sample_val)
        if len(self._buffers[channel_name]) > max_samples:
            self._buffers[channel_name].pop(0)

        x_data = range(len(self._buffers[channel_name]))
        data_item = self._channel_data_items[channel_name]
        data_item.setVisible(visible)
        data_item.setData(x_data, self._buffers[channel_name])


class MultiStreamNumericContainer(QtWidgets.QWidget):
    """Container stacking multiple SingleStreamNumericPlotWidget widgets.

    Attributes:
        _layout: The main QtWidgets.QVBoxLayout for this container widget.
        _stream_plots: Maps stream names to SingleStreamNumericPlotWidget.
    """

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        """Initializes the container for multiple numeric streams.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._layout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout()
        self.setLayout(self._layout)
        self._stream_plots: Dict[str, SingleStreamNumericPlotWidget] = {}

    def update_numeric_containers(
        self, stream_name: str, channel_name: str, sample_val: float, visible: bool
    ) -> None:
        """Updates data for a specific channel in a numeric stream.

        Creates a new stream widget if it's the first time the stream is encountered.
        (lazy initialization)

        Args:
            stream_name: The name of the numeric stream.
            channel_name: The fully qualified channel identifier
                (e.g. "Eyetracking:Gaze_X").
            sample_val: The new data sample.
            visible: Whether the channel should be visible.
        """
        if stream_name not in self._stream_plots:
            plot_widget = SingleStreamNumericPlotWidget(stream_name)
            self._stream_plots[stream_name] = plot_widget
            self._layout.addWidget(plot_widget)

        self._stream_plots[stream_name].update_data(channel_name, sample_val, visible)
