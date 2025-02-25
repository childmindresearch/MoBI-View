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
    expected_title = "MoBI_View"
    expected_status = "Status: OK"
    expected_stream_types = ["EEGStream", "GazeStream"]
    expected_top_level_count = 0

    title = main_app_view.windowTitle()
    status_bar = main_app_view.statusBar()
    current_status = cast(QStatusBar, status_bar).currentMessage() if status_bar else ""
    stream_types = list(main_app_view._stream_types.keys())
    top_level_count = main_app_view._tree_widget.topLevelItemCount()

    assert title == expected_title
    assert status_bar is not None
    assert current_status == expected_status
    assert main_app_view._channel_visibility == {}
    assert main_app_view._stream_channels == {}
    assert stream_types == expected_stream_types
    assert top_level_count == expected_top_level_count


def test_update_plot_eeg(main_app_view: MainAppView) -> None:
    """Verifies that updating an EEG stream populates the EEG tab and control panel.

    Args:
        main_app_view: The MainAppView instance from the fixture.

    Asserts:
        - After adding channels and updating with data, the top-level tree item
          for "EEGStream" exists and has two children.
    """
    stream_name = "EEGStream"
    chan1 = f"{stream_name}:ChanA"
    chan2 = f"{stream_name}:ChanB"
    expected_channels = {chan1, chan2}
    data = {
        "stream_name": stream_name,
        "data": [1.0, 2.0],
        "channel_labels": ["ChanA", "ChanB"],
    }
    main_app_view.add_tree_item(stream_name, chan1)
    main_app_view.add_tree_item(stream_name, chan2)
    main_app_view._channel_visibility[chan1] = True
    main_app_view._channel_visibility[chan2] = True
    main_app_view._stream_channels[stream_name] = expected_channels

    main_app_view.update_plot(data)
    top_item = main_app_view._stream_items[stream_name]
    child_count = top_item.childCount()
    child_texts = [
        cast(QTreeWidgetItem, top_item.child(i)).text(0)
        for i in range(child_count)
        if top_item.child(i) is not None
    ]

    assert top_item.text(0) == stream_name
    assert child_count == 2
    for text in child_texts:
        assert text in ("ChanA", "ChanB")


def test_update_plot_non_eeg(main_app_view: MainAppView) -> None:
    """Verifies that updating a non-EEG stream populates the numeric tab and ctrl panel.

    Args:
        main_app_view: The MainAppView instance from the fixture.

    Asserts:
        - After adding a channel for "GazeStream" and updating with data, the
          corresponding tree item exists with one child.
    """
    stream_name = "GazeStream"
    chan = f"{stream_name}:GazeX"
    data = {
        "stream_name": stream_name,
        "data": [3.14],
        "channel_labels": ["GazeX"],
    }
    main_app_view.add_tree_item(stream_name, chan)
    main_app_view._channel_visibility[chan] = True
    main_app_view._stream_channels[stream_name] = {chan}

    main_app_view.update_plot(data)
    top_item = main_app_view._stream_items[stream_name]

    assert top_item.text(0) == stream_name
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
    new_visibility = False

    main_app_view.set_plot_channel_visibility(chan_name, new_visibility)

    assert main_app_view._channel_visibility[chan_name] is new_visibility


def test_display_error(
    main_app_view: MainAppView, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verifies that display_error updates the status bar message.

    Using Monkeypatch to replace QMessageBox.critical with a dummy function
    to avoid displaying a dialog.

    Args:
        main_app_view: The MainAppView instance from the fixture.
        monkeypatch: Pytest fixture for patching attributes.

    Asserts:
        - After calling display_error, the status bar shows the error message.
    """
    error_text = "Something went wrong!"

    def dummy_critical(*args: object, **kwargs: object) -> None:
        return None

    monkeypatch.setattr(
        "MoBI_View.views.main_app_view.QMessageBox.critical", dummy_critical
    )

    main_app_view.display_error(error_text)
    status_bar = main_app_view.statusBar()
    current_status = cast(QStatusBar, status_bar).currentMessage() if status_bar else ""

    expected_status = f"Status: {error_text}"
    assert status_bar is not None
    assert current_status == expected_status


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
