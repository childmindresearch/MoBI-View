"""Unit tests for the MainAppView class in the MoBI_View package.

Tests cover initial state, updating plots for EEG and non-EEG streams, toggling
channel visibility, error display, and tree item changes.
"""

from typing import Dict, List, Tuple, cast

import pytest
from PyQt6 import QtCore, QtWidgets

from MoBI_View.views import main_app_view


@pytest.fixture
def test_data() -> Dict:
    """Returns common test data for all tests.

    Returns:
        A dictionary containing test channel names, stream names, and sample values.
    """
    return {
        "eeg_stream": "EEGStream",
        "gaze_stream": "GazeStream",
        "test_stream": "TestStream",
        "unknown_stream": "UnknownStream",
        "eeg_channel1": "EEGStream:ChanA",
        "eeg_channel2": "EEGStream:ChanB",
        "gaze_channel": "GazeStream:GazeX",
        "test_channel1": "TestStream:Chan1",
        "test_channel2": "TestStream:Chan2",
        "eeg_values": [1.0, 2.0],
        "gaze_values": [3.14],
        "empty_values": [],
        "eeg_labels": ["ChanA", "ChanB"],
        "gaze_labels": ["GazeX"],
        "empty_labels": [],
        "window_title": "MoBI_View",
        "status_ok": "Status: OK",
        "error_message": "Something went wrong!",
        "stream_info": {"EEGStream": "EEG", "GazeStream": "Gaze"},
    }


@pytest.fixture
def app_view(
    qt_app: QtWidgets.QApplication, test_data: Dict
) -> main_app_view.MainAppView:
    """Creates a basic MainAppView instance.

    Args:
        qt_app: The QApplication instance.
        test_data: Dictionary containing test values.

    Returns:
        An instance of MainAppView.
    """
    return main_app_view.MainAppView(stream_info=test_data["stream_info"])


@pytest.fixture
def tree_setup(
    app_view: main_app_view.MainAppView, test_data: Dict
) -> Tuple[
    QtWidgets.QTreeWidgetItem,
    QtWidgets.QTreeWidgetItem,
    QtWidgets.QTreeWidgetItem,
]:
    """Adds tree items to an existing app_view for visibility tests.

    Args:
        app_view: The MainAppView instance.
        test_data: Dictionary containing test values.

    Returns:
        Tuple of (parent, child1, child2) tree widget items.
    """
    app_view.add_tree_item(test_data["test_stream"], test_data["test_channel1"])
    app_view.add_tree_item(test_data["test_stream"], test_data["test_channel2"])

    stream_item = app_view._stream_items[test_data["test_stream"]]
    child1 = app_view._channel_items[test_data["test_channel1"]]
    child2 = app_view._channel_items[test_data["test_channel2"]]

    stream_item.setCheckState(0, QtCore.Qt.CheckState.Checked)
    child1.setCheckState(0, QtCore.Qt.CheckState.Checked)
    child2.setCheckState(0, QtCore.Qt.CheckState.Checked)

    return stream_item, child1, child2


def test_initial_state(app_view: main_app_view.MainAppView, test_data: Dict) -> None:
    """Checks the initial setup of MainAppView.

    Verifies window title, status bar message, empty visibility map, and
    stream registration upon initialization.

    Args:
        app_view: The MainAppView instance.
        test_data: Dictionary containing test values.
    """
    expected_title = test_data["window_title"]
    expected_status = test_data["status_ok"]
    expected_visibility: Dict[str, bool] = {}
    expected_stream_types = sorted([test_data["eeg_stream"], test_data["gaze_stream"]])
    expected_tree_item_count = 0

    status_bar = app_view.statusBar()
    actual_status = (
        cast(QtWidgets.QStatusBar, status_bar).currentMessage() if status_bar else ""
    )
    actual_stream_types = sorted(list(app_view._stream_types.keys()))
    actual_tree_item_count = app_view._tree_widget.topLevelItemCount()

    assert app_view.windowTitle() == expected_title
    assert actual_status == expected_status
    assert app_view._channel_visibility == expected_visibility
    assert actual_stream_types == expected_stream_types
    assert actual_tree_item_count == expected_tree_item_count


@pytest.mark.parametrize(
    "stream_key,values_key,labels_key,channel_keys,expected_count",
    [
        ("eeg_stream", "eeg_values", "eeg_labels", ["eeg_channel1", "eeg_channel2"], 2),
        ("gaze_stream", "gaze_values", "gaze_labels", ["gaze_channel"], 1),
    ],
    ids=["eeg_stream", "gaze_stream"],
)
def test_update_plot(
    app_view: main_app_view.MainAppView,
    test_data: Dict,
    stream_key: str,
    values_key: str,
    labels_key: str,
    channel_keys: List[str],
    expected_count: int,
) -> None:
    """Tests updating plots for different stream types.

    Verifies that data updates create the expected tree structure and
    appropriate child items for both EEG and non-EEG streams.

    Args:
        app_view: The MainAppView instance.
        test_data: Dictionary containing test values.
        stream_key: Key in test_data for the stream name.
        values_key: Key in test_data for the values.
        labels_key: Key in test_data for the channel labels.
        channel_keys: List of keys in test_data for channel names.
        expected_count: Expected number of child items.
    """
    for channel_key in channel_keys:
        app_view.add_tree_item(test_data[stream_key], test_data[channel_key])
        app_view._channel_visibility[test_data[channel_key]] = True

    data = {
        "stream_name": test_data[stream_key],
        "data": test_data[values_key],
        "channel_labels": test_data[labels_key],
    }

    app_view.update_plot(data)

    top_item = app_view._stream_items[test_data[stream_key]]
    child_texts = []
    for idx in range(top_item.childCount()):
        child = top_item.child(idx)
        if child is not None:
            child_texts.append(child.text(0))

    assert top_item.text(0) == test_data[stream_key]
    assert top_item.childCount() == expected_count
    assert all(
        expected_label in child_texts for expected_label in test_data[labels_key]
    )


def test_update_plot_empty_data(
    app_view: main_app_view.MainAppView, test_data: Dict
) -> None:
    """Tests updating a plot with empty data.

    Verifies that the application handles empty data gracefully without errors.

    Args:
        app_view: The MainAppView instance.
        test_data: Dictionary containing test values.
    """
    app_view.add_tree_item(test_data["eeg_stream"], test_data["eeg_channel1"])
    app_view._channel_visibility[test_data["eeg_channel1"]] = True

    data = {
        "stream_name": test_data["eeg_stream"],
        "data": test_data["empty_values"],
        "channel_labels": test_data["empty_labels"],
    }

    app_view.update_plot(data)

    assert test_data["eeg_stream"] in app_view._stream_items


def test_update_plot_unknown_stream(
    app_view: main_app_view.MainAppView, test_data: Dict
) -> None:
    """Tests updating a plot with an unknown stream type.

    Verifies that data with an unknown stream type is handled properly.

    Args:
        app_view: The MainAppView instance.
        test_data: Dictionary containing test values.
    """
    unknown_channel = f"{test_data['unknown_stream']}:Channel"
    data = {
        "stream_name": test_data["unknown_stream"],
        "data": [1.0],
        "channel_labels": ["Channel"],
    }

    app_view.add_tree_item(test_data["unknown_stream"], unknown_channel)
    app_view._channel_visibility[unknown_channel] = True
    app_view.update_plot(data)

    assert test_data["unknown_stream"] in app_view._stream_items


def test_set_plot_channel_visibility(
    app_view: main_app_view.MainAppView, test_data: Dict
) -> None:
    """Tests setting channel visibility.

    Verifies that the visibility state of a channel can be correctly updated
    through the API.

    Args:
        app_view: The MainAppView instance.
        test_data: Dictionary containing test values.
    """
    chan_name = test_data["eeg_channel1"]
    app_view._channel_visibility[chan_name] = True

    app_view.set_plot_channel_visibility(chan_name, False)

    assert app_view._channel_visibility[chan_name] is False


def test_display_error(
    app_view: main_app_view.MainAppView,
    test_data: Dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tests error display functionality.

    Verifies that error messages are properly displayed in the status bar.
    Uses monkeypatch to prevent actual QMessageBox from appearing during tests.

    Args:
        app_view: The MainAppView instance.
        test_data: Dictionary containing test values.
        monkeypatch: Pytest fixture for patching attributes.
    """
    error_text = test_data["error_message"]

    monkeypatch.setattr(
        "PyQt6.QtWidgets.QMessageBox.critical",
        lambda *args, **kwargs: None,
    )

    app_view.display_error(error_text)
    status_bar = app_view.statusBar()
    current_status = status_bar.currentMessage() if status_bar is not None else ""

    assert current_status == f"Status: {error_text}"


def test_on_tree_item_changed_top_level(
    app_view: main_app_view.MainAppView, tree_setup: Tuple
) -> None:
    """Tests toggling a top-level tree item.

    Verifies that when a parent stream item is toggled, all its child
    channel items reflect the same checked state.

    Args:
        app_view: The MainAppView instance.
        tree_setup: Tuple with (app_view, parent, child1, child2) items.
    """
    stream_item, child1, child2 = tree_setup

    stream_item.setCheckState(0, QtCore.Qt.CheckState.Unchecked)
    app_view._on_tree_item_changed(stream_item)

    assert child1.checkState(0) == QtCore.Qt.CheckState.Unchecked
    assert child2.checkState(0) == QtCore.Qt.CheckState.Unchecked


def test_on_tree_item_changed_child(
    app_view: main_app_view.MainAppView, tree_setup: Tuple, test_data: Dict
) -> None:
    """Tests toggling a child tree item.

    Verifies that toggling a channel item updates the internal visibility
    tracking dictionary to match the UI state.

    Args:
        app_view: The MainAppView instance.
        tree_setup: Tuple with (app_view, parent, child1, child2) items.
        test_data: Dictionary containing test values.
    """
    _, child1, _ = tree_setup

    child1.setCheckState(0, QtCore.Qt.CheckState.Unchecked)
    app_view._on_tree_item_changed(child1)

    assert app_view._channel_visibility[test_data["test_channel1"]] is False
