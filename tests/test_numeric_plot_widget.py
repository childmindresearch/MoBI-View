"""Unit tests for numeric_plot_widget in the MoBI_View package.

Tests cover channel addition, updating data, buffer overflow, and duplicate channel
handling for SingleStreamNumericPlotWidget and MultiStreamNumericContainer.
"""

from typing import Dict, Generator

import pyqtgraph as pg
import pytest
from PyQt6 import QtWidgets

from MoBI_View import config, exceptions
from MoBI_View.views.numeric_plot_widget import (
    MultiStreamNumericContainer,
    SingleStreamNumericPlotWidget,
)


# Check if module level means this script and not the EEG script, or it should be class?
@pytest.fixture(scope="module")
def qt_app() -> Generator[QtWidgets.QApplication, None, None]:
    """Creates a QtWidgets.QApplication instance for tests.

    Yields:
        A QtWidgets.QApplication instance.
    """
    app = QtWidgets.QApplication([])
    pg.setConfigOption("useOpenGL", False)
    yield app
    app.quit()


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
) -> SingleStreamNumericPlotWidget:
    """Creates a SingleStreamNumericPlotWidget for testing.

    Args:
        qt_app: The QtWidgets.QApplication instance.
        test_data: Dictionary containing test data values.

    Returns:
        A SingleStreamNumericPlotWidget instance with the test stream name.
    """
    widget = SingleStreamNumericPlotWidget(test_data["stream_name"])
    return widget


@pytest.fixture
def populated_widget(
    single_widget: SingleStreamNumericPlotWidget, test_data: Dict
) -> SingleStreamNumericPlotWidget:
    """Creates a SingleStreamNumericPlotWidget with a channel already added.

    Args:
        single_widget: A base SingleStreamNumericPlotWidget instance.
        test_data: Dictionary containing test data values.

    Returns:
        A SingleStreamNumericPlotWidget with a test channel already added.
    """
    single_widget.add_channel(test_data["first_channel"])
    return single_widget


@pytest.fixture
def container(qt_app: QtWidgets.QApplication) -> MultiStreamNumericContainer:
    """Creates a MultiStreamNumericContainer for testing.

    Args:
        qt_app: The QtWidgets.QApplication instance.

    Returns:
        A MultiStreamNumericContainer instance.
    """
    return MultiStreamNumericContainer()


def test_single_widget_add_channel(
    populated_widget: SingleStreamNumericPlotWidget, test_data: Dict
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

# Parameterize?
def test_update_data_visible(
    populated_widget: SingleStreamNumericPlotWidget, test_data: Dict
) -> None:
    """Tests updating data with visibility set to True.

    Args:
        populated_widget: A SingleStreamNumericPlotWidget fixture with a channel already
            added.
        test_data: Dictionary containing test data values.
    """
    channel = test_data["first_channel"]
    sample = test_data["visible_sample"]

    populated_widget.update_data(channel, sample, True)

    assert len(populated_widget._buffers[channel]) == 1
    assert populated_widget._buffers[channel][0] == sample
    assert populated_widget._channel_data_items[channel].isVisible()


def test_update_data_overflow(
    populated_widget: SingleStreamNumericPlotWidget, test_data: Dict
) -> None:
    """Tests that buffer respects MAX_SAMPLES limit.

    Args:
        populated_widget: A SingleStreamNumericPlotWidget fixture with a channel already
            added.
        test_data: Dictionary containing test data values.
    """
    channel = test_data["first_channel"]
    populated_widget._buffers[channel] = test_data["initial_buffer"]
    populated_widget.update_data(channel, test_data["overflow_sample"], True)

    assert len(populated_widget._buffers[channel]) == config.Config.MAX_SAMPLES
    assert populated_widget._buffers[channel][-1] == test_data["overflow_sample"]
    assert populated_widget._buffers[channel][0] == test_data["initial_buffer"][1]


def test_update_data_hidden(
    populated_widget: SingleStreamNumericPlotWidget, test_data: Dict
) -> None:
    """Tests updating data when visibility is set to False.

    Args:
        populated_widget: A SingleStreamNumericPlotWidget fixture with a channel already
            added.
        test_data: Dictionary containing test data values.
    """
    channel = test_data["first_channel"]

    populated_widget.update_data(channel, test_data["hidden_sample"], False)

    assert populated_widget._buffers[channel][-1] == test_data["hidden_sample"]
    assert not populated_widget._channel_data_items[channel].isVisible()


def test_add_duplicate_channel(
    populated_widget: SingleStreamNumericPlotWidget, test_data: Dict
) -> None:
    """Verifies that add_channel returns immediately when the channel already exists.

    Args:
        populated_widget: A SingleStreamNumericPlotWidget fixture with a channel already
            added.
        test_data: Dictionary containing test data values.
    """
    channel = test_data["first_channel"]
    state_before = {
        "data_items": populated_widget._channel_data_items.copy(),
        "buffers": populated_widget._buffers.copy(),
    }

    with pytest.raises(
        exceptions.DuplicateChannelLabelError,
        match="Unable to add a duplicate channel label under the same stream.",
    ):
        populated_widget.add_channel(channel)
    assert populated_widget._channel_data_items == state_before["data_items"]
    assert populated_widget._buffers == state_before["buffers"]


def test_auto_channel_creation(
    single_widget: SingleStreamNumericPlotWidget, test_data: Dict
) -> None:
    """Tests channel is automatically created when data is updated to an empty widget.

    Args:
        single_widget: An empty SingleStreamNumericPlotWidget fixture.
        test_data: Dictionary containing test data values.
    """
    channel = test_data["first_channel"]

    single_widget.update_data(channel, test_data["visible_sample"], True)

    assert channel in single_widget._channel_data_items
    assert channel in single_widget._buffers
    assert single_widget._buffers[channel] == [test_data["visible_sample"]]


@pytest.mark.parametrize("visibility", [True, False])
def test_visibility_setting(
    populated_widget: SingleStreamNumericPlotWidget, test_data: Dict, visibility: bool
) -> None:
    """Tests that visibility setting works correctly.

    Args:
        populated_widget: A SingleStreamNumericPlotWidget fixture with a channel already
            added.
        test_data: Dictionary containing test data values.
        visibility: Boolean parameter for testing both visibility states.
    """
    channel = test_data["first_channel"]

    populated_widget.update_data(channel, test_data["visible_sample"], visibility)

    assert populated_widget._channel_data_items[channel].isVisible() is visibility


def test_container_creates_widgets(
    container: MultiStreamNumericContainer, test_data: Dict
) -> None:
    """Tests that MultiStreamNumericContainer creates stream widgets as needed.

    Args:
        container: Empty MultiStreamNumericContainer fixture.
        test_data: Dictionary containing test data values.
    """
    stream = test_data["stream_name"]
    channel = test_data["first_channel"]

    container.update_numeric_containers(
        stream, channel, test_data["visible_sample"], True
    )
    # assert stream in container._stream_plots
    widget = container._stream_plots[stream]

    assert channel in widget._channel_data_items


def test_container_updates_existing_channels(
    container: MultiStreamNumericContainer, test_data: Dict
) -> None:
    """Tests that MultiStreamNumericContainer updates existing channels correctly.

    Args:
        container: Empty MultiStreamNumericContainer fixture.
        test_data: Dictionary containing test data values.
    """
    stream = test_data["stream_name"]
    first_channel = test_data["first_channel"]
    second_channel = test_data["second_channel"]

    container.update_numeric_containers(
        stream, first_channel, test_data["visible_sample"], True
    )
    container.update_numeric_containers(
        stream, second_channel, test_data["hidden_sample"], False
    )

    widget = container._stream_plots[stream]
    assert first_channel in widget._channel_data_items
    assert second_channel in widget._channel_data_items
    assert widget._channel_data_items[second_channel].isVisible() is False
