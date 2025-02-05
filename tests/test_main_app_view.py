"""Unit tests for the MainAppView class in the MoBI_View package, using real PyQt widgets."""

import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from MoBI_View.views.main_app_view import MainAppView


@pytest.fixture(scope="module")
def qt_app():
    """Creates a QApplication instance for all tests in this module."""
    app = QApplication([])
    yield app
    app.quit()


@pytest.fixture
def main_app_view(qt_app) -> MainAppView:
    """Creates a real instance of MainAppView with minimal stream info."""
    stream_info = {
        "EEGStream": "EEG",
        "GazeStream": "Gaze",
    }
    return MainAppView(stream_info=stream_info)


def test_initial_state(main_app_view: MainAppView) -> None:
    """
    Checks the initial setup of MainAppView following Arrange–Act–Assert.
    """
    expected_title = "MoBI_View"
    expected_label_text = "Status: OK"
    expected_top_level_item_count = 0

    actual_title = main_app_view.windowTitle()
    actual_label_text = main_app_view._status_label.text()
    actual_channel_visibility = main_app_view._channel_visibility
    actual_stream_channels = main_app_view._stream_channels
    actual_stream_types_keys = main_app_view._stream_types.keys()
    actual_top_level_count = main_app_view._tree_widget.topLevelItemCount()

    assert actual_title == expected_title
    assert actual_channel_visibility == {}
    assert actual_stream_channels == {}
    assert "EEGStream" in actual_stream_types_keys
    assert "GazeStream" in actual_stream_types_keys
    assert actual_label_text == expected_label_text
    assert actual_top_level_count == expected_top_level_item_count


def test_update_plot_eeg(main_app_view: MainAppView) -> None:
    """
    Verifies that updating an EEG stream populates the EEG tab and control panel, using AAA.
    """
    data = {
        "stream_name": "EEGStream",
        "data": [1.0, 2.0],
    }
    expected_stream_name = data["stream_name"]
    expected_num_channels = len(data["data"])

    main_app_view.update_plot(data)
    top_item = main_app_view._stream_items[expected_stream_name]
    actual_top_item_text = top_item.text(0)
    actual_top_item_state = top_item.checkState(0)
    actual_child_count = top_item.childCount()

    assert actual_top_item_text == expected_stream_name
    assert actual_top_item_state == Qt.CheckState.Checked
    assert actual_child_count == expected_num_channels

    for i, sample_val in enumerate(data["data"], start=1):
        ch_name = f"{expected_stream_name}:Channel{i}"
        assert ch_name in main_app_view._channel_visibility
        assert ch_name in main_app_view._stream_channels[expected_stream_name]
        assert main_app_view._channel_visibility[ch_name] is True

        child_item = top_item.child(i - 1)
        actual_child_text = child_item.text(0)
        assert actual_child_text == f"Channel{i}"


def test_update_plot_non_eeg(main_app_view: MainAppView) -> None:
    """
    Verifies that updating a non-EEG stream populates the numeric tab, using AAA.
    """
    data = {
        "stream_name": "GazeStream",
        "data": [3.14, -2.7],
    }
    expected_stream_name = data["stream_name"]
    expected_num_channels = len(data["data"])

    main_app_view.update_plot(data)
    top_item = main_app_view._stream_items[expected_stream_name]
    actual_top_item_text = top_item.text(0)
    actual_child_count = top_item.childCount()

    assert actual_top_item_text == expected_stream_name
    assert actual_child_count == expected_num_channels

    for i, sample_val in enumerate(data["data"], start=1):
        ch_name = f"{expected_stream_name}:Channel{i}"
        assert ch_name in main_app_view._channel_visibility
        assert ch_name in main_app_view._stream_channels[expected_stream_name]

        child_item = top_item.child(i - 1)
        actual_child_text = child_item.text(0)
        assert actual_child_text == f"Channel{i}"


def test_set_plot_channel_visibility(main_app_view: MainAppView) -> None:
    """
    Verifies set_plot_channel_visibility changes the internal visibility mapping, using AAA.
    """
    channel_name = "EEGStream:Channel1"
    main_app_view._channel_visibility[channel_name] = True
    new_visibility = False

    main_app_view.set_plot_channel_visibility(channel_name, new_visibility)
    actual_visibility = main_app_view._channel_visibility[channel_name]

    assert actual_visibility == new_visibility


def test_display_error(main_app_view: MainAppView) -> None:
    """
    Verifies display_error updates the status label, using AAA.
    """
    error_message = "Something went wrong!"
    expected_status_label = f"Status: {error_message}"

    main_app_view.display_error(error_message)
    actual_label_text = main_app_view._status_label.text()

    assert actual_label_text == expected_status_label
