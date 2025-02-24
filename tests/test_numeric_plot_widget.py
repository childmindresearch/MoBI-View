"""Unit tests for numeric_plot_widget in the MoBI_View package.

Tests cover channel addition, updating data, buffer overflow, and duplicate channel
handling for SingleStreamNumericPlotWidget and MultiStreamNumericContainer.
"""

from typing import Generator

import pyqtgraph as pg
import pytest
from PyQt6.QtWidgets import QApplication

from MoBI_View.views.numeric_plot_widget import (
    MAX_SAMPLES,
    MultiStreamNumericContainer,
    SingleStreamNumericPlotWidget,
)


@pytest.fixture(scope="module")
def qt_app() -> Generator[QApplication, None, None]:
    """Creates a QApplication instance for tests.

    Returns:
        A QApplication instance.
    """
    app = QApplication([])
    pg.setConfigOption("useOpenGL", False)
    yield app
    app.quit()


def test_single_stream_numeric_plot_widget_add_and_update(
    qt_app: QApplication,
) -> None:
    """Tests for adding a channel and updating data in SingleStreamNumericPlotWidget.

    Args:
        qt_app: The QApplication instance from the fixture.

    Asserts:
        - The channel is added to internal dictionaries.
        - Updating data appends to the buffer and respects MAX_SAMPLES.
    """
    widget = SingleStreamNumericPlotWidget("TestStream")
    chan = "TestStream:ChanA"
    widget.add_channel(chan)
    assert chan in widget._channel_data_items
    assert chan in widget._buffers
    widget.update_data(chan, 3.14, True)
    assert len(widget._buffers[chan]) == 1
    widget._buffers[chan] = [2.72] * MAX_SAMPLES
    widget.update_data(chan, 4.56, True)
    assert len(widget._buffers[chan]) == MAX_SAMPLES
    assert widget._buffers[chan][-1] == 4.56
    widget.update_data(chan, 5.0, False)
    assert widget._buffers[chan][-1] == 5.0


def test_multi_stream_numeric_container(qt_app: QApplication) -> None:
    """Tests that MultiStreamNumericContainer creates and updates stream widgets.

    Args:
        qt_app: The QApplication instance from the fixture.

    Asserts:
        - A new stream widget is created when a stream is updated.
        - Channels are added and updated correctly within the stream widget.
    """
    container = MultiStreamNumericContainer()
    sname = "NumStream1"
    cname = "NumStream1:ChanX"
    assert sname not in container._stream_plots
    container.update_data(sname, cname, 10.0, True)
    assert sname in container._stream_plots
    widget = container._stream_plots[sname]
    assert cname in widget._channel_data_items
    cname2 = "NumStream1:ChanY"
    container.update_data(sname, cname2, -5.0, True)
    assert cname2 in widget._channel_data_items
    container.update_data(sname, cname, 20.0, False)
    assert widget._buffers[cname][-1] == 20.0


def test_add_channel_duplicate_numeric(qt_app: QApplication) -> None:
    """Verifies that add_channel returns immediately when the channel already exists.

    Args:
        qt_app: The QApplication instance from the fixture.

    Asserts:
        - Internal state remains unchanged when adding a duplicate channel.
    """
    widget = SingleStreamNumericPlotWidget("TestStream")
    chan = "TestStream:F1"
    widget.add_channel(chan)
    state_before = {
        "data_items": widget._channel_data_items.copy(),
        "buffers": widget._buffers.copy(),
    }
    widget.add_channel(chan)
    assert widget._channel_data_items == state_before["data_items"]
    assert widget._buffers == state_before["buffers"]
