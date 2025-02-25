"""Module providing widgets for EEG data visualization in MoBI_View.

Displays all EEG data in a single PlotWidget with each channel vertically offset
and labeled. Only the bottom axis is shown.
"""

from typing import Dict, List

import numpy as np
import pyqtgraph as pg
from PyQt6.QtWidgets import QVBoxLayout, QWidget

MAX_SAMPLES = 500
OFFSET = 50.0


class EEGPlotWidget(QWidget):
    """Displays all EEG data in one PlotWidget with vertical offsets and labels.

    Attributes:
        _layout: The main QVBoxLayout for this widget.
        _plot_widget: The pyqtgraph PlotWidget used to display EEG signals.
        _buffers: Maps each channel name to a list of float samples.
        _data_items: Maps each channel name to its PlotDataItem in the PlotWidget.
        _channel_order: Maps each channel name to an integer index for offset order.
        _text_items: Maps each channel name to its text label item in the PlotWidget.
        _channel_visible: Maps each channel name to a bool indicating visibility.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initializes the EEGPlotWidget.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._layout: QVBoxLayout = QVBoxLayout()
        self.setLayout(self._layout)

        self._plot_widget = pg.PlotWidget()
        self._plot_widget.showGrid(x=True, y=True)
        self._plot_widget.getAxis("left").setStyle(showValues=False)
        self._layout.addWidget(self._plot_widget)

        self._buffers: Dict[str, List[float]] = {}
        self._data_items: Dict[str, pg.PlotDataItem] = {}
        self._channel_order: Dict[str, int] = {}
        self._text_items: Dict[str, pg.TextItem] = {}
        self._channel_visible: Dict[str, bool] = {}

    def add_channel(self, chan_name: str) -> None:
        """Adds a new channel with its vertical offset and label.

        Args:
            chan_name: Full identifier, e.g. "EEGStream:Fz".
        """
        if chan_name in self._channel_order:
            return
        idx = len(self._channel_order)
        self._channel_order[chan_name] = idx
        self._buffers[chan_name] = []
        self._channel_visible[chan_name] = True

        pen = pg.mkPen(width=1, color="w")
        data_item = self._plot_widget.plot([], [], pen=pen)
        self._data_items[chan_name] = data_item

        text_item = pg.TextItem(
            text=chan_name.split(":", 1)[-1], color="w", anchor=(1, 0.5)
        )
        text_item.setPos(-10, idx * OFFSET)
        self._plot_widget.addItem(text_item)
        self._text_items[chan_name] = text_item

    def update_data(self, chan_name: str, sample_val: float, visible: bool) -> None:
        """Appends a new sample to a channel's buffer and updates its plot.

        Reassigns offsets if visibility changes, to remove or restore gaps.

        Args:
            chan_name: Full channel identifier.
            sample_val: The new sample value.
            visible: Whether the channel should be visible.
        """
        if chan_name not in self._channel_order:
            self.add_channel(chan_name)

        self._buffers[chan_name].append(sample_val)
        if len(self._buffers[chan_name]) > MAX_SAMPLES:
            self._buffers[chan_name].pop(0)

        old_vis = self._channel_visible[chan_name]
        if old_vis != visible:
            self._channel_visible[chan_name] = visible
            self._reassign_offsets()

        data_item = self._data_items[chan_name]
        data_item.setVisible(visible)
        text_item = self._text_items[chan_name]
        text_item.setVisible(visible)

        idx = self._channel_order[chan_name]
        x_data = np.arange(len(self._buffers[chan_name]))
        offset = idx * OFFSET
        y_data = np.array(self._buffers[chan_name]) + offset
        data_item.setData(x_data, y_data)

    def _reassign_offsets(self) -> None:
        """Reassigns offsets among only the visible channels to avoid gaps."""
        visible_chs = [ch for ch in self._channel_order if self._channel_visible[ch]]
        visible_chs.sort(key=lambda ch: self._channel_order[ch])

        for new_idx, ch in enumerate(visible_chs):
            self._channel_order[ch] = new_idx
            self._text_items[ch].setPos(-10, new_idx * OFFSET)

        for ch in visible_chs:
            buf = self._buffers[ch]
            idx = self._channel_order[ch]
            x_data = np.arange(len(buf))
            y_data = np.array(buf) + idx * OFFSET
            self._data_items[ch].setData(x_data, y_data)
