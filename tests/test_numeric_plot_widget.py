"""Unit tests for numeric_plot_widget in the MoBI_View package.

Tests cover channel addition, updating data, buffer overflow, and duplicate channel
handling for SingleStreamNumericPlotWidget and MultiStreamNumericContainer.
"""

from typing import Dict

import pytest
from PyQt6 import QtWidgets

from MoBI_View.core import config, exceptions
from MoBI_View.views import numeric_plot_widget


@pytest.fixture
def test_data() -> Dict:
    """Returns a dictionary with common test data for all tests.

    Returns:
        A dictionary containing test stream names, channel names, and sample values.
    """
    return {
        "stream_name": "TestStream",
        "first_channel": "TestStream:ChanA",
        "second_channel": "TestStream:ChanB",
        "visible_sample": 1.23,
        "overflow_sample": 4.56,
        "hidden_sample": 7.89,
        "initial_buffer": [0.12] * config.Config.MAX_SAMPLES,
    }


@pytest.fixture
def single_widget(
    qt_app: QtWidgets.QApplication, test_data: Dict
) -> numeric_plot_widget.SingleStreamNumericPlotWidget:
    """Creates an empty SingleStreamNumericPlotWidget for testing.

    Args:
        qt_app: The QApplication instance.
        test_data: Dictionary containing test data values.

    Returns:
        A SingleStreamNumericPlotWidget instance with the test stream name.
    """
    return numeric_plot_widget.SingleStreamNumericPlotWidget(test_data["stream_name"])


@pytest.fixture
def populated_widget(
    single_widget: numeric_plot_widget.SingleStreamNumericPlotWidget,
    test_data: Dict,
) -> numeric_plot_widget.SingleStreamNumericPlotWidget:
    """Creates a SingleStreamNumericPlotWidget with a channel.

    Args:
        single_widget: A base SingleStreamNumericPlotWidget instance.
        test_data: Dictionary containing test data values.

    Returns:
        A SingleStreamNumericPlotWidget with a test channel already added.
    """
    single_widget.add_channel(test_data["first_channel"])
    return single_widget


def test_single_widget_add_channel(
    populated_widget: numeric_plot_widget.SingleStreamNumericPlotWidget,
    test_data: Dict,
) -> None:
    """Tests that adding a channel properly initializes internal structures.

    Args:
        populated_widget: A SingleStreamNumericPlotWidget with a channel already added.
        test_data: Dictionary containing test data values.
    """
    channel = test_data["first_channel"]

    assert channel in populated_widget._channel_data_items
    assert channel in populated_widget._buffers
    assert populated_widget._buffers[channel] == []


@pytest.mark.parametrize("visible", [True, False])
def test_update_data(
    populated_widget: numeric_plot_widget.SingleStreamNumericPlotWidget,
    test_data: Dict,
    visible: bool,
) -> None:
    """Tests updating data with different visibility settings.

    Args:
        populated_widget: A SingleStreamNumericPlotWidget with a channel already added.
        test_data: Dictionary containing test data values.
        visible: Whether the channel should be visible.
    """
    channel = test_data["first_channel"]
    sample = test_data["visible_sample"] if visible else test_data["hidden_sample"]

    populated_widget.update_data(channel, sample, visible)

    assert len(populated_widget._buffers[channel]) == 1
    assert populated_widget._buffers[channel][0] == sample
    assert populated_widget._channel_data_items[channel].isVisible() is visible


def test_update_data_overflow(
    populated_widget: numeric_plot_widget.SingleStreamNumericPlotWidget,
    test_data: Dict,
) -> None:
    """Tests that buffer respects MAX_SAMPLES limit.

    Args:
        populated_widget: A SingleStreamNumericPlotWidget with a channel already added.
        test_data: Dictionary containing test data values.
    """
    channel = test_data["first_channel"]
    populated_widget._buffers[channel] = test_data["initial_buffer"]
    populated_widget.update_data(channel, test_data["overflow_sample"], True)

    assert len(populated_widget._buffers[channel]) == config.Config.MAX_SAMPLES
    assert populated_widget._buffers[channel][-1] == test_data["overflow_sample"]
    assert populated_widget._buffers[channel][0] == test_data["initial_buffer"][1]


def test_add_duplicate_channel(
    populated_widget: numeric_plot_widget.SingleStreamNumericPlotWidget,
    test_data: Dict,
) -> None:
    """Verifies that add_channel returns immediately when the channel already exists.

    Args:
        populated_widget: A SingleStreamNumericPlotWidget with a channel already added.
        test_data: Dictionary containing test data values.
    """
    channel = test_data["first_channel"]

    with pytest.raises(
        exceptions.DuplicateChannelLabelError,
        match="Unable to add a duplicate channel label under the same stream.",
    ):
        populated_widget.add_channel(channel)


def test_auto_channel_creation(
    single_widget: numeric_plot_widget.SingleStreamNumericPlotWidget,
    test_data: Dict,
) -> None:
    """Tests channel is automatically created when data is updated to an empty widget.

    Args:
        single_widget: A base SingleStreamNumericPlotWidget instance.
        test_data: Dictionary containing test data values.
    """
    channel = test_data["first_channel"]

    single_widget.update_data(channel, test_data["visible_sample"], True)

    assert channel in single_widget._channel_data_items
    assert channel in single_widget._buffers
    assert single_widget._buffers[channel] == [test_data["visible_sample"]]


@pytest.mark.parametrize("visibility", [True, False])
def test_visibility_setting(
    populated_widget: numeric_plot_widget.SingleStreamNumericPlotWidget,
    test_data: Dict,
    visibility: bool,
) -> None:
    """Tests that visibility setting works correctly.

    Args:
        populated_widget: A SingleStreamNumericPlotWidget with a channel already added.
        test_data: Dictionary containing test data values.
        visibility: Boolean parameter for testing both visibility states.
    """
    channel = test_data["first_channel"]

    populated_widget.update_data(channel, test_data["visible_sample"], visibility)

    assert populated_widget._channel_data_items[channel].isVisible() is visibility


def test_container_creates_widgets(
    qt_app: QtWidgets.QApplication, test_data: Dict
) -> None:
    """Tests that MultiStreamNumericContainer creates stream widgets as needed.

    Args:
        qt_app: The QApplication instance for the test.
        container: Empty MultiStreamNumericContainer fixture.
        test_data: Dictionary containing test data values.
    """
    container = numeric_plot_widget.MultiStreamNumericContainer()
    stream = test_data["stream_name"]
    channel = test_data["first_channel"]

    container.update_numeric_containers(
        stream, channel, test_data["visible_sample"], True
    )

    assert stream in container._stream_plots
    assert channel in container._stream_plots[stream]._channel_data_items


def test_container_updates_existing_channels(
    qt_app: QtWidgets.QApplication, test_data: Dict
) -> None:
    """Tests that MultiStreamNumericContainer updates existing channels correctly.

    Tests the update function of MultiStreamNumericContainer.

    Args:
        qt_app: The QApplication instance for the test.
        container: Empty MultiStreamNumericContainer fixture.
        test_data: Dictionary containing test data values.
    """
    container = numeric_plot_widget.MultiStreamNumericContainer()
    stream = test_data["stream_name"]
    first_channel = test_data["first_channel"]
    second_channel = test_data["second_channel"]

    container.update_numeric_containers(
        stream, first_channel, test_data["visible_sample"], True
    )
    container.update_numeric_containers(
        stream, second_channel, test_data["hidden_sample"], False
    )

    assert first_channel in container._stream_plots[stream]._channel_data_items
    assert second_channel in container._stream_plots[stream]._channel_data_items
    assert (
        container._stream_plots[stream]._channel_data_items[second_channel].isVisible()
        is False
    )
