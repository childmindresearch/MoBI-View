"""Unit tests for the EEGPlotWidget in the MoBI_View package.

Tests cover channel addition, updating data with toggling visibility and
offset reassignment, buffer overflow, and duplicate channel addition.
"""

from typing import Generator

import pyqtgraph as pg
import pytest
from PyQt6.QtWidgets import QApplication

from MoBI_View.views.eeg_plot_widget import MAX_SAMPLES, EEGPlotWidget


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


def test_add_channel(qt_app: QApplication) -> None:
    """Tests that adding a channel registers it in internal dictionaries.

    Args:
        qt_app: The QApplication instance from the fixture.

    Asserts:
        - The channel identifier is added to _channel_order, _buffers, and
          _channel_visible.
    """
    widget = EEGPlotWidget()
    chan = "EEGStream:Fz"
    widget.add_channel(chan)
    assert chan in widget._channel_order
    assert chan in widget._buffers
    assert chan in widget._channel_visible


def test_add_channel_duplicate(qt_app: QApplication) -> None:
    """Verifies that calling add_channel twice does not modify internal state.

    Args:
        qt_app: The QApplication instance from the fixture.

    Asserts:
        - Internal dictionaries remain unchanged when a duplicate channel is added.
    """
    widget = EEGPlotWidget()
    chan = "EEGStream:Fz"
    widget.add_channel(chan)
    state_before = {
        "order": widget._channel_order.copy(),
        "buffers": widget._buffers.copy(),
        "visible": widget._channel_visible.copy(),
        "text": widget._text_items.copy(),
    }
    widget.add_channel(chan)
    assert widget._channel_order == state_before["order"]
    assert widget._buffers == state_before["buffers"]
    assert widget._channel_visible == state_before["visible"]
    assert widget._text_items == state_before["text"]


def test_update_data_visibility_toggle(qt_app: QApplication) -> None:
    """Tests updating data while toggling visibility and triggering offset reassignment.

    Args:
        qt_app: The QApplication instance from the fixture.

    Asserts:
        - The buffers are updated.
        - Visibility flags change appropriately.
    """
    widget = EEGPlotWidget()
    c1 = "EEG:Cz"
    c2 = "EEG:Pz"
    widget.update_data(c1, 1.0, True)
    widget.update_data(c2, 2.0, True)
    assert len(widget._buffers[c1]) == 1
    assert len(widget._buffers[c2]) == 1
    widget.update_data(c1, 3.0, False)
    assert widget._channel_visible[c1] is False
    assert widget._channel_visible[c2] is True
    widget.update_data(c1, 4.0, True)
    assert widget._channel_visible[c1] is True
    assert len(widget._buffers[c1]) == 3


def test_update_data_overflow(qt_app: QApplication) -> None:
    """Tests that the buffer length does not exceed MAX_SAMPLES.

    Args:
        qt_app: The QApplication instance from the fixture.

    Asserts:
        - After adding more than MAX_SAMPLES, the buffer size equals MAX_SAMPLES.
    """
    widget = EEGPlotWidget()
    chan = "EEGStream:Oz"
    for _ in range(MAX_SAMPLES + 5):
        widget.update_data(chan, 1.23, True)
    assert len(widget._buffers[chan]) == MAX_SAMPLES
    assert widget._buffers[chan][-1] == 1.23


def test_reassign_offsets(qt_app: QApplication) -> None:
    """Tests that reassign_offsets reindexes visible channels to avoid gaps.

    Args:
        qt_app: The QApplication instance from the fixture.

    Asserts:
        - After toggling channels, the visible channels are re-indexed consecutively.
    """
    widget = EEGPlotWidget()
    c1 = "EEGStream:A"
    c2 = "EEGStream:B"
    c3 = "EEGStream:C"
    widget.update_data(c1, 0.1, True)
    widget.update_data(c2, 0.2, True)
    widget.update_data(c3, 0.3, True)
    assert widget._channel_order[c1] == 0
    assert widget._channel_order[c2] == 1
    assert widget._channel_order[c3] == 2
    widget.update_data(c2, 0.4, False)
    assert widget._channel_visible[c2] is False
    assert widget._channel_order[c1] == 0
    assert widget._channel_order[c3] == 1
    widget.update_data(c2, 0.5, True)
    visible = [ch for ch in widget._channel_visible if widget._channel_visible[ch]]
    assert len(visible) == 3
    used_indices = sorted(widget._channel_order[ch] for ch in visible)
    assert used_indices == [0, 1, 2]