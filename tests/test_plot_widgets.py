"""Unit tests for EEGPlotWidget and numeric plot widgets in MoBI_View."""

from typing import Generator

import pytest
import pyqtgraph as pg
from PyQt6.QtWidgets import QApplication

from MoBI_View.views.eeg_plot_widget import EEGPlotWidget
from MoBI_View.views.numeric_plot_widget import (
    SingleStreamNumericPlotWidget,
    MultiStreamNumericContainer,
)


@pytest.fixture(scope="module")
def qt_app() -> Generator[QApplication, None, None]:
    """Creates a QApplication instance for tests."""
    app = QApplication([])
    pg.setConfigOption("useOpenGL", False)
    yield app
    app.quit()


def test_eeg_plot_widget_add_and_update(qt_app: QApplication) -> None:
    """Tests adding a channel and updating data for EEGPlotWidget."""
    widget = EEGPlotWidget()
    test_channel = "EEGStream:Fz"
    widget.add_channel(test_channel)
    # Exercise the branch that returns immediately if channel exists.
    widget.add_channel(test_channel)
    widget.update_data(test_channel, 1.23, True)
    buffer_list = widget._buffers[test_channel]
    assert buffer_list == [1.23]
    # Force buffer overflow: fill buffer to MAX_SAMPLES and add one more value.
    widget._buffers[test_channel] = [0.0] * 500
    widget.update_data(test_channel, 1.23, True)
    assert len(widget._buffers[test_channel]) == 500
    assert widget._buffers[test_channel][-1] == 1.23
    # Test hidden branch.
    widget.update_data(test_channel, 2.34, False)
    assert widget._buffers[test_channel][-1] == 1.23


def test_numeric_plot_widget_add_and_update(qt_app: QApplication) -> None:
    """Tests adding a channel and updating data for SingleStreamNumericPlotWidget."""
    widget = SingleStreamNumericPlotWidget("TestStream")
    test_channel = "TestStream:F1"
    widget.add_channel(test_channel)
    widget.update_data(test_channel, 3.14, True)
    buffer_list = widget._buffers[test_channel]
    assert buffer_list == [3.14]
    # Force buffer overflow.
    widget._buffers[test_channel] = [0.0] * 500
    widget.update_data(test_channel, 3.14, True)
    assert len(widget._buffers[test_channel]) == 500
    assert widget._buffers[test_channel][-1] == 3.14
    # Test hidden branch.
    widget.update_data(test_channel, 2.71, False)
    assert widget._buffers[test_channel][-1] == 3.14


def test_multi_stream_numeric_container(qt_app: QApplication) -> None:
    """Tests that MultiStreamNumericContainer creates and updates stream widgets."""
    container = MultiStreamNumericContainer()
    stream_name = "TestStream"
    channel_name = "TestStream:F1"
    assert stream_name not in container._stream_plots
    container.update_data(stream_name, channel_name, 1.0, True)
    assert stream_name in container._stream_plots
    widget = container._stream_plots[stream_name]
    widget.update_data(channel_name, 2.0, True)
    buffer_list = widget._buffers[channel_name]
    assert buffer_list == [1.0, 2.0]
