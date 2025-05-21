"""Smoke tests for MoBI-View application using real LSL streams.

Tests the application's main entry point with actual LSL streams while using
mock UI components to prevent test blocking and unwanted windows.
"""

import importlib
import sys
import time
from typing import Dict, Generator, List, cast

import numpy as np
import pytest
from pylsl import StreamInfo, StreamOutlet

import MoBI_View.main


class MockQApp:
    """Mock QApplication that prevents UI display during tests."""

    def __init__(self, *args: object) -> None:
        """Initialize mock QApplication."""
        pass

    def exec(self) -> int:
        """Return immediately instead of blocking with event loop."""
        return 0


class MockMainAppView:
    """Mock MainAppView that tracks method calls instead of rendering UI."""

    init_params: Dict[str, object] = {}
    instances: List["MockMainAppView"] = []
    tree_items: Dict[str, List[str]]

    def __init__(self, **kwargs: object) -> None:
        """Initialize with tracking for method calls and parameters."""
        MockMainAppView.init_params.update(kwargs)
        MockMainAppView.instances.append(self)

        self.stream_info = kwargs.get("stream_info", {})
        self.show_called = False
        self.channel_visibility: Dict[str, bool] = {}

    def show(self) -> None:
        """Track that show was called."""
        self.show_called = True

    def set_plot_channel_visibility(self, channel_name: str, visible: bool) -> None:
        """Record channel visibility changes."""
        self.channel_visibility[channel_name] = visible

    def update_plot(self, stream_name: str, data: object) -> None:
        """Record plot updates without updating UI."""
        pass

    def display_error(self, message: str) -> None:
        """Print error messages instead of displaying in UI."""
        print(f"ERROR: {message}")

    def add_tree_item(self, parent_name: str, item_name: str) -> None:
        """Mock implementation to track tree item additions.

        Args:
            parent_name: Name of the parent item (stream name)
            item_name: Name of the item to add (channel name)
        """
        if not hasattr(self, "tree_items"):
            self.tree_items: Dict[str, List[str]] = {}

        if parent_name not in self.tree_items:
            self.tree_items[parent_name] = []

        self.tree_items[parent_name].append(item_name)

    @classmethod
    def reset(cls) -> None:
        """Reset all class variables for clean test state."""
        cls.init_params.clear()
        cls.instances.clear()


@pytest.fixture
def eeg_stream() -> Generator[StreamOutlet, None, None]:
    """Create a real EEG LSL stream for testing.

    Returns:
        A live LSL outlet transmitting mock EEG data.
    """
    info = StreamInfo(
        name="TestEEG",
        type="EEG",
        channel_count=4,
        nominal_srate=100,
        channel_format="float32",
        source_id="smoketest_eeg",
    )

    channels = info.desc().append_child("channels")
    for i in range(4):
        channels.append_child("channel").append_child_value(
            "label", f"EEG{i + 1}"
        ).append_child_value("type", "EEG").append_child_value("unit", "uV")

    outlet = StreamOutlet(info)
    outlet.push_sample(np.zeros(4))
    yield outlet
    del outlet


@pytest.fixture
def accel_stream() -> Generator[StreamOutlet, None, None]:
    """Create a real Accelerometer LSL stream for testing.

    Returns:
        A live LSL outlet transmitting mock accelerometer data.
    """
    info = StreamInfo(
        name="TestAccel",
        type="Accelerometer",
        channel_count=3,
        nominal_srate=50,
        channel_format="float32",
        source_id="smoketest_accel",
    )

    channels = info.desc().append_child("channels")
    labels = ["X", "Y", "Z"]
    for i, label in enumerate(labels):
        channels.append_child("channel").append_child_value(
            "label", label
        ).append_child_value("type", "Accelerometer").append_child_value("unit", "g")

    outlet = StreamOutlet(info)
    outlet.push_sample(np.zeros(3))
    yield outlet
    del outlet


@pytest.fixture(autouse=True)
def reset_mock_state() -> Generator[None, None, None]:
    """Reset mock state before each test."""
    MockMainAppView.reset()
    yield


def test_main_with_real_streams(
    eeg_stream: StreamOutlet,
    accel_stream: StreamOutlet,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
) -> None:
    """Test main() function with real LSL streams.

    Uses real streams for data flow while mocking UI components. We patch objects
    before reloading the main module to ensure our mocks are used during execution.
    Module reloading ensures the code runs with our mocks instead of the original
    implementations.

    Args:
        eeg_stream: Real EEG stream fixture
        accel_stream: Real accelerometer stream fixture
        monkeypatch: Fixture for patching objects
        capsys: Fixture for capturing stdout/stderr
    """
    for _ in range(5):
        eeg_stream.push_sample(np.random.rand(4))
        accel_stream.push_sample(np.random.rand(3))

    time.sleep(0.5)

    monkeypatch.setattr("PyQt6.QtWidgets.QApplication", MockQApp)
    monkeypatch.setattr("MoBI_View.views.main_app_view.MainAppView", MockMainAppView)
    monkeypatch.setattr(sys, "exit", lambda x: None)

    importlib.reload(MoBI_View.main)

    MoBI_View.main.main()
    captured = capsys.readouterr()
    created_view = MockMainAppView.instances[0]
    stream_info = cast(Dict[str, str], MockMainAppView.init_params["stream_info"])

    assert len(MockMainAppView.instances) > 0
    assert "TestEEG" in captured.out
    assert "TestAccel" in captured.out
    assert "Type=EEG" in captured.out
    assert "Type=Accelerometer" in captured.out
    assert "stream_info" in MockMainAppView.init_params
    assert MockMainAppView.init_params["stream_info"] != {}
    assert "TestEEG" in stream_info
    assert "TestAccel" in stream_info
    assert stream_info["TestEEG"] == "EEG"
    assert stream_info["TestAccel"] == "Accelerometer"
    assert created_view.show_called
    assert "TestEEG" in created_view.tree_items
    assert "TestAccel" in created_view.tree_items


def test_main_no_streams(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
) -> None:
    """Test main() function when no LSL streams are available.

    Mocks the stream resolution to return an empty list and verifies the application
    handles this case correctly. We patch objects before reloading the main module
    to ensure our mocks are used during execution.

    Args:
        monkeypatch: Fixture for patching objects
        capsys: Fixture for capturing stdout/stderr
    """
    monkeypatch.setattr("pylsl.resolve_streams", lambda: [])
    monkeypatch.setattr("PyQt6.QtWidgets.QApplication", MockQApp)
    monkeypatch.setattr("MoBI_View.views.main_app_view.MainAppView", MockMainAppView)
    monkeypatch.setattr(sys, "exit", lambda x: None)

    importlib.reload(MoBI_View.main)

    MoBI_View.main.main()
    captured = capsys.readouterr()
    created_view = MockMainAppView.instances[0]

    assert "stream_info" in MockMainAppView.init_params
    assert MockMainAppView.init_params["stream_info"] == {}
    assert "Resolving LSL streams..." in captured.out
    assert len(MockMainAppView.instances) > 0
    assert created_view.show_called
