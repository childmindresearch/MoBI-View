"""Unit tests for the MainAppView class in the MoBI_View package.

Tests cover initial state, updating plots for EEG and non-EEG streams, toggling
channel visibility, error display, and tree item changes.
"""

from typing import Generator, cast

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QStatusBar, QTreeWidgetItem

from MoBI_View.views.main_app_view import MainAppView


@pytest.fixture(scope="module")
def qt_app() -> Generator[QApplication, None, None]:
    """Creates a QApplication instance for all tests in this module.

    Returns:
        A QApplication instance.
    """
    app = QApplication([])
    yield app
    app.quit()


@pytest.fixture
def main_app_view(qt_app: QApplication) -> MainAppView:
    """Creates a real instance of MainAppView with minimal stream info.

    Args:
        qt_app: The QApplication instance provided by the fixture.

    Returns:
        An instance of MainAppView.
    """
    stream_info = {"EEGStream": "EEG", "GazeStream": "Gaze"}
    return MainAppView(stream_info=stream_info)


def test_initial_state(main_app_view: MainAppView) -> None:
    """Checks the initial setup of MainAppView.

    Args:
        main_app_view: The MainAppView instance from the fixture.

    Asserts:
        - The window title is "MoBI_View".
        - The status bar shows "Status: OK".
        - Internal dictionaries (_channel_visibility and _stream_channels) are empty.
        - _stream_types contains the expected stream names.
        - The tree widget has no top-level items.
    """
    assert main_app_view.windowTitle() == "MoBI_View"
    status_bar = main_app_view.statusBar()
    assert status_bar is not None
    assert cast(QStatusBar, status_bar).currentMessage() == "Status: OK"
    assert main_app_view._channel_visibility == {}
    assert main_app_view._stream_channels == {}
    types_keys = list(main_app_view._stream_types.keys())
    assert types_keys == ["EEGStream", "GazeStream"]
    assert main_app_view._tree_widget.topLevelItemCount() == 0


def test_update_plot_eeg(main_app_view: MainAppView) -> None:
    """Verifies that updating an EEG stream populates the EEG tab and control panel.

    Args:
        main_app_view: The MainAppView instance from the fixture.

    Asserts:
        - After adding channels and updating with data, the top-level tree item for
          "EEGStream" exists and has two children.
    """
    main_app_view.add_tree_item("EEGStream", "EEGStream:ChanA")
    main_app_view.add_tree_item("EEGStream", "EEGStream:ChanB")
    main_app_view._channel_visibility["EEGStream:ChanA"] = True
    main_app_view._channel_visibility["EEGStream:ChanB"] = True
    main_app_view._stream_channels["EEGStream"] = {"EEGStream:ChanA",
                                                   "EEGStream:ChanB"}
    data = {
        "stream_name": "EEGStream",
        "data": [1.0, 2.0],
        "channel_labels": ["ChanA", "ChanB"],
    }
    main_app_view.update_plot(data)
    top_item = main_app_view._stream_items["EEGStream"]
    assert top_item.text(0) == "EEGStream"
    assert top_item.childCount() == 2
    cA_item = top_item.child(0)
    cB_item = top_item.child(1)
    assert cA_item is not None
    assert cB_item is not None
    assert cA_item.text(0) in ("ChanA", "ChanB")
    assert cB_item.text(0) in ("ChanA", "ChanB")


def test_update_plot_non_eeg(main_app_view: MainAppView) -> None:
    """Verifies that updating a non-EEG stream populates the numeric tab and ctrl panel.

    Args:
        main_app_view: The MainAppView instance from the fixture.

    Asserts:
        - After adding a channel for "GazeStream" and updating with data, the
          corresponding tree item exists with one child.
    """
    main_app_view.add_tree_item("GazeStream", "GazeStream:GazeX")
    main_app_view._channel_visibility["GazeStream:GazeX"] = True
    main_app_view._stream_channels["GazeStream"] = {"GazeStream:GazeX"}
    data = {
        "stream_name": "GazeStream",
        "data": [3.14],
        "channel_labels": ["GazeX"],
    }
    main_app_view.update_plot(data)
    top_item = main_app_view._stream_items["GazeStream"]
    assert top_item.text(0) == "GazeStream"
    assert top_item.childCount() == 1


def test_set_plot_channel_visibility(main_app_view: MainAppView) -> None:
    """Verifies that set_plot_channel_visibility updates the internal mapping.

    Args:
        main_app_view: The MainAppView instance from the fixture.

    Asserts:
        - The _channel_visibility for a given channel is updated correctly.
    """
    chan_name = "EEGStream:Channel1"
    main_app_view._channel_visibility[chan_name] = True
    main_app_view.set_plot_channel_visibility(chan_name, False)
    assert main_app_view._channel_visibility[chan_name] is False


def test_display_error(main_app_view: MainAppView) -> None:
    """Verifies that display_error updates the status bar message.

    Args:
        main_app_view: The MainAppView instance from the fixture.

    Asserts:
        - After calling display_error, the status bar shows the error message.
    """
    main_app_view.display_error("Something went wrong!")
    status_bar = main_app_view.statusBar()
    assert status_bar is not None
    error_message = "Status: Something went wrong!"
    assert cast(QStatusBar, status_bar).currentMessage() == error_message


def test_reset_control_panel(main_app_view: MainAppView) -> None:
    """Verifies that reset_control_panel makes the dock widget visible.

    Args:
        main_app_view: The MainAppView instance from the fixture.

    Asserts:
        - After hiding the dock and calling reset_control_panel, the dock is visible.
    """
    main_app_view._dock.hide()
    main_app_view.reset_control_panel()
    assert main_app_view._dock.isVisible()


def test_on_tree_item_changed_top_level(main_app_view: MainAppView) -> None:
    """Tests that toggling a top-level tree item toggles all its child items.

    Args:
        main_app_view: The MainAppView instance from the fixture.

    Asserts:
        - When the top-level item is unchecked, all child items become unchecked.
    """
    stream_item = QTreeWidgetItem()
    stream_item.setText(0, "TestStream")
    main_app_view._tree_widget.addTopLevelItem(stream_item)
    child1 = QTreeWidgetItem(stream_item)
    child1.setText(0, "Chan1")
    child1.setCheckState(0, Qt.CheckState.Checked)
    child2 = QTreeWidgetItem(stream_item)
    child2.setText(0, "Chan2")
    child2.setCheckState(0, Qt.CheckState.Checked)
    main_app_view._stream_items["TestStream"] = stream_item
    main_app_view._channel_items["TestStream:Chan1"] = child1
    main_app_view._channel_items["TestStream:Chan2"] = child2
    main_app_view._channel_visibility["TestStream:Chan1"] = True
    main_app_view._channel_visibility["TestStream:Chan2"] = True
    stream_item.setCheckState(0, Qt.CheckState.Unchecked)
    main_app_view._on_tree_item_changed(stream_item)
    assert child1.checkState(0) == Qt.CheckState.Unchecked
    assert child2.checkState(0) == Qt.CheckState.Unchecked


def test_on_tree_item_changed_child(main_app_view: MainAppView) -> None:
    """Tests that toggling a child tree item updates the corresponding visibility.

    Args:
        main_app_view: The MainAppView instance from the fixture.

    Asserts:
        - When a child item is unchecked, the internal _channel_visibility is updated.
    """
    stream_item = QTreeWidgetItem()
    stream_item.setText(0, "TestStream")
    main_app_view._tree_widget.addTopLevelItem(stream_item)
    child = QTreeWidgetItem(stream_item)
    child.setText(0, "ChanX")
    child.setCheckState(0, Qt.CheckState.Checked)
    main_app_view._stream_items["TestStream"] = stream_item
    main_app_view._channel_items["TestStream:ChanX"] = child
    main_app_view._channel_visibility["TestStream:ChanX"] = True
    child.setCheckState(0, Qt.CheckState.Unchecked)
    main_app_view._on_tree_item_changed(child)
    assert main_app_view._channel_visibility["TestStream:ChanX"] is False
