"""Unit tests for the MainAppView class in the MoBI_View package,
using real PyQt widgets.
"""

from typing import Generator, cast

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QTreeWidgetItem, QStatusBar

from MoBI_View.views.main_app_view import MainAppView


@pytest.fixture(scope="module")
def qt_app() -> Generator[QApplication, None, None]:
    """Creates a QApplication instance for all tests in this module."""
    app = QApplication([])
    yield app
    app.quit()


@pytest.fixture
def main_app_view(qt_app: QApplication) -> MainAppView:
    """Creates a real instance of MainAppView with minimal stream info."""
    stream_info = {"EEGStream": "EEG", "GazeStream": "Gaze"}
    return MainAppView(stream_info=stream_info)


def test_initial_state(main_app_view: MainAppView) -> None:
    """Checks the initial setup of MainAppView."""
    expected_title = "MoBI_View"
    expected_message = "Status: OK"
    expected_top_level_item_count = 0

    actual_title = main_app_view.windowTitle()
    status_bar = main_app_view.statusBar()
    if status_bar is None:
        raise RuntimeError("Status bar is None")
    actual_message = cast(QStatusBar, status_bar).currentMessage()
    actual_stream_types_keys = list(main_app_view._stream_types.keys())
    actual_top_level_count = main_app_view._tree_widget.topLevelItemCount()

    assert actual_title == expected_title
    assert main_app_view._channel_visibility == {}
    assert main_app_view._stream_channels == {}
    assert "EEGStream" in actual_stream_types_keys
    assert "GazeStream" in actual_stream_types_keys
    assert actual_message == expected_message
    assert actual_top_level_count == expected_top_level_item_count


def test_update_plot_eeg(main_app_view: MainAppView) -> None:
    """Verifies that updating an EEG stream populates the EEG tab and control panel."""
    data = {
        "stream_name": "EEGStream",
        "data": [1.0, 2.0],
        "channel_labels": ["Channel1", "Channel2"],
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

    for i in range(1, expected_num_channels + 1):
        ch_name = f"{expected_stream_name}:Channel{i}"
        assert ch_name in main_app_view._channel_visibility
        assert ch_name in cast(
            set[str], main_app_view._stream_channels[expected_stream_name]
        )
        assert main_app_view._channel_visibility[ch_name] is True
        child_item = top_item.child(i - 1)
        if child_item is None:
            raise RuntimeError("Child item missing")
        actual_child_text = child_item.text(0)
        assert actual_child_text == f"Channel{i}"


def test_update_plot_non_eeg(main_app_view: MainAppView) -> None:
    """Verifies that updating a non-EEG stream populates the numeric tab."""
    data = {
        "stream_name": "GazeStream",
        "data": [3.14, -2.7],
        "channel_labels": ["Channel1", "Channel2"],
    }
    expected_stream_name = data["stream_name"]
    expected_num_channels = len(data["data"])

    main_app_view.update_plot(data)
    top_item = main_app_view._stream_items[expected_stream_name]
    actual_top_item_text = top_item.text(0)
    actual_child_count = top_item.childCount()

    assert actual_top_item_text == expected_stream_name
    assert actual_child_count == expected_num_channels

    for i in range(1, expected_num_channels + 1):
        ch_name = f"{expected_stream_name}:Channel{i}"
        assert ch_name in main_app_view._channel_visibility
        assert ch_name in cast(
            set[str], main_app_view._stream_channels[expected_stream_name]
        )
        child_item = top_item.child(i - 1)
        if child_item is None:
            raise RuntimeError("Child item missing")
        actual_child_text = child_item.text(0)
        assert actual_child_text == f"Channel{i}"


def test_set_plot_channel_visibility(main_app_view: MainAppView) -> None:
    """Verifies set_plot_channel_visibility changes the internal visibility mapping."""
    channel_name = "EEGStream:Channel1"
    main_app_view._channel_visibility[channel_name] = True
    new_visibility = False

    main_app_view.set_plot_channel_visibility(channel_name, new_visibility)
    actual_visibility = main_app_view._channel_visibility[channel_name]
    assert actual_visibility == new_visibility


def test_display_error(main_app_view: MainAppView) -> None:
    """Verifies display_error updates the status label."""
    error_message = "Something went wrong!"
    expected_status_label = f"Status: {error_message}"
    main_app_view.display_error(error_message)
    status_bar = main_app_view.statusBar()
    if status_bar is None:
        raise RuntimeError("Status bar is None")
    actual_label_text = cast(QStatusBar, status_bar).currentMessage()
    assert actual_label_text == expected_status_label


def test_reset_control_panel(main_app_view: MainAppView) -> None:
    """Verifies reset_control_panel shows the control panel dock widget."""
    main_app_view._dock.hide()
    assert not main_app_view._dock.isVisible()
    main_app_view.reset_control_panel()
    assert main_app_view._dock.isVisible()


def test_setup_status_bar_error(main_app_view: MainAppView) -> None:
    """Verifies _setup_status_bar raises an error if status bar is None."""
    original_status_bar = main_app_view.statusBar
    main_app_view.statusBar = lambda: None
    with pytest.raises(RuntimeError, match="Status bar not set"):
        main_app_view._setup_status_bar()
    main_app_view.statusBar = original_status_bar


def test_add_tree_item_error(main_app_view: MainAppView) -> None:
    """Verifies add_tree_item raises an error if parent item is None."""
    main_app_view._stream_items["FaultyStream"] = None
    with pytest.raises(RuntimeError, match="Parent item missing"):
        main_app_view.add_tree_item("FaultyStream", "FaultyStream:Channel1")


def test_display_error_status_bar_none(main_app_view: MainAppView) -> None:
    """Verifies display_error raises an error if status bar is None."""
    original_status_bar = main_app_view.statusBar
    main_app_view.statusBar = lambda: None
    with pytest.raises(RuntimeError, match="Status bar not set"):
        main_app_view.display_error("Test error")
    main_app_view.statusBar = original_status_bar
