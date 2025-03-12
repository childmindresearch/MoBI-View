"""Unit tests for eeg_plot_widget in the MoBI_View package."""

from typing import Dict

import pytest
from PyQt6 import QtWidgets

from MoBI_View.core import config, exceptions
from MoBI_View.views import eeg_plot_widget


@pytest.fixture
def test_data() -> Dict:
    """Returns common test data for all tests.

    Returns:
        A dictionary containing test channel names and sample values.
    """
    return {
        "first_channel": "EEGStream:Fz",
        "second_channel": "EEGStream:Cz",
        "third_channel": "EEGStream:Pz",
        "sample_value": 1.23,
        "offset": config.Config.EEG_OFFSET,
        "initial_buffer": [4.56] * config.Config.MAX_SAMPLES,
    }


@pytest.fixture
def populated_widget(
    qt_app: QtWidgets.QApplication, test_data: Dict
) -> eeg_plot_widget.EEGPlotWidget:
    """Creates an EEGPlotWidget with a channel already added.

    Args:
        qt_app: The QApplication instance.
        test_data: Dictionary containing test data values.

    Returns:
        An EEGPlotWidget with a test channel already added.
    """
    widget = eeg_plot_widget.EEGPlotWidget()
    widget.add_channel(test_data["first_channel"])
    return widget


def test_add_channel(
    populated_widget: eeg_plot_widget.EEGPlotWidget, test_data: Dict
) -> None:
    """Tests that adding a channel properly initializes internal structures.

    Args:
        populated_widget: An EEGPlotWidget with a channel already added.
        test_data: Dictionary containing test data values.
    """
    channel = test_data["first_channel"]
    expected_label = channel.split(":", 1)[-1]

    assert populated_widget._channel_order[channel] == 0
    assert populated_widget._buffers[channel] == []
    assert populated_widget._channel_visible[channel] is True
    assert channel in populated_widget._data_items
    assert populated_widget._text_items[channel].toPlainText() == expected_label


def test_add_duplicate_channel(
    populated_widget: eeg_plot_widget.EEGPlotWidget, test_data: Dict
) -> None:
    """Tests that adding a duplicate channel raises an exception.

    Args:
        populated_widget: An EEGPlotWidget with a channel already added.
        test_data: Dictionary containing test data values.
    """
    with pytest.raises(
        exceptions.DuplicateChannelLabelError,
        match="Unable to add a duplicate channel label to EEG plot.",
    ):
        populated_widget.add_channel(test_data["first_channel"])


@pytest.mark.parametrize("visibility", [True, False])
def test_update_data(
    populated_widget: eeg_plot_widget.EEGPlotWidget, test_data: Dict, visibility: bool
) -> None:
    """Tests updating data with different visibility settings.

    Args:
        populated_widget: An EEGPlotWidget with a channel already added.
        test_data: Dictionary containing test data values.
        visibility: Boolean parameter for testing both visibility states.
    """
    channel = test_data["first_channel"]
    sample = test_data["sample_value"]

    populated_widget.update_data(channel, sample, visibility)

    assert len(populated_widget._buffers[channel]) == 1
    assert populated_widget._buffers[channel][0] == sample
    assert populated_widget._channel_visible[channel] is visibility
    assert populated_widget._data_items[channel].isVisible() is visibility
    assert populated_widget._text_items[channel].isVisible() is visibility


def test_update_data_overflow(
    populated_widget: eeg_plot_widget.EEGPlotWidget, test_data: Dict
) -> None:
    """Tests that buffer respects MAX_SAMPLES limit.

    Args:
        populated_widget: An EEGPlotWidget with a channel already added.
        test_data: Dictionary containing test data values.
    """
    channel = test_data["first_channel"]
    populated_widget._buffers[channel] = test_data["initial_buffer"].copy()
    overflow_sample = test_data["sample_value"]

    populated_widget.update_data(channel, overflow_sample, True)

    assert len(populated_widget._buffers[channel]) == config.Config.MAX_SAMPLES
    assert populated_widget._buffers[channel][-1] == overflow_sample
    assert populated_widget._buffers[channel][0] == test_data["initial_buffer"][1]


def test_auto_channel_creation(qt_app: QtWidgets.QApplication, test_data: Dict) -> None:
    """Tests channel is automatically created when data is updated to a new channel.

    Args:
        qt_app: The QApplication instance.
        test_data: Dictionary containing test data values.
    """
    widget = eeg_plot_widget.EEGPlotWidget()

    widget.update_data(test_data["first_channel"], test_data["sample_value"], True)

    assert test_data["first_channel"] in widget._channel_order
    assert test_data["first_channel"] in widget._buffers
    assert widget._buffers[test_data["first_channel"]] == [test_data["sample_value"]]


def test_showing_hidden_channel_restores_order(
    qt_app: QtWidgets.QApplication, test_data: Dict
) -> None:
    """Tests that showing a hidden channel restores proper order.

    Args:
        qt_app: The QApplication instance.
        test_data: Dictionary containing test data values.
    """
    widget = eeg_plot_widget.EEGPlotWidget()

    widget.add_channel(test_data["first_channel"])
    widget.add_channel(test_data["second_channel"])
    widget.add_channel(test_data["third_channel"])
    widget.update_data(test_data["second_channel"], test_data["sample_value"], False)
    widget.update_data(test_data["second_channel"], test_data["sample_value"], True)

    assert widget._channel_order[test_data["first_channel"]] == 0
    assert widget._channel_order[test_data["second_channel"]] == 1
    assert widget._channel_order[test_data["third_channel"]] == 2
