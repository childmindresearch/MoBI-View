"""Smoke tests for MoBI-View application using real LSL streams.

Tests the application's ability to discover and connect to LSL streams.
"""

import time
from typing import Generator
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from pylsl import info as pylsl_info
from pylsl import outlet as pylsl_outlet
from pylsl import resolve as pylsl_resolve

from MoBI_View import main
from MoBI_View.core import data_inlet


@pytest.fixture
def eeg_stream() -> Generator[pylsl_outlet.StreamOutlet, None, None]:
    """Create a real EEG LSL stream for testing.

    Returns:
        A live LSL outlet transmitting mock EEG data.
    """
    info = pylsl_info.StreamInfo(
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

    outlet = pylsl_outlet.StreamOutlet(info)
    outlet.push_sample(np.zeros(4))
    yield outlet
    del outlet


@pytest.fixture
def accel_stream() -> Generator[pylsl_outlet.StreamOutlet, None, None]:
    """Create a real Accelerometer LSL stream for testing.

    Returns:
        A live LSL outlet transmitting mock accelerometer data.
    """
    info = pylsl_info.StreamInfo(
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

    outlet = pylsl_outlet.StreamOutlet(info)
    outlet.push_sample(np.zeros(3))
    yield outlet
    del outlet


def test_data_inlet_with_real_streams(
    eeg_stream: pylsl_outlet.StreamOutlet,
    accel_stream: pylsl_outlet.StreamOutlet,
) -> None:
    """Test DataInlet with real LSL streams.

    Uses real streams to verify data acquisition works correctly.

    Args:
        eeg_stream: Real EEG stream fixture
        accel_stream: Real accelerometer stream fixture
    """
    for _ in range(5):
        eeg_stream.push_sample(np.random.rand(4))
        accel_stream.push_sample(np.random.rand(3))
    time.sleep(0.5)

    discovered_streams = pylsl_resolve.resolve_streams()
    data_inlets = []
    for info in discovered_streams:
        inlet = data_inlet.DataInlet(info)
        data_inlets.append(inlet)
    stream_names = {inlet.stream_name for inlet in data_inlets}
    eeg_inlet = next(i for i in data_inlets if i.stream_name == "TestEEG")
    accel_inlet = next(i for i in data_inlets if i.stream_name == "TestAccel")

    assert len(data_inlets) >= 2, "Should discover at least 2 streams"
    assert "TestEEG" in stream_names
    assert "TestAccel" in stream_names
    assert eeg_inlet.channel_count == 4
    assert eeg_inlet.stream_type == "EEG"
    assert len(eeg_inlet.channel_info["labels"]) == 4
    assert accel_inlet.channel_count == 3
    assert accel_inlet.stream_type == "Accelerometer"
    assert len(accel_inlet.channel_info["labels"]) == 3


def test_no_streams() -> None:
    """Test behavior when no LSL streams are available.

    This test runs without any fixtures to verify handling of empty stream list.
    """
    discovered_streams = pylsl_resolve.resolve_streams(wait_time=0.1)
    test_streams = [s for s in discovered_streams if "Test" in s.name()]

    if len(test_streams) == 0:
        data_inlets = []
        for info in discovered_streams:
            inlet = data_inlet.DataInlet(info)
            data_inlets.append(inlet)

        assert isinstance(data_inlets, list)


def test_main_discovers_streams_and_starts_server() -> None:
    """Tests main() wires discovery, presenter, browser launch, and server."""
    mock_inlet = MagicMock()
    mock_presenter = MagicMock()

    with (
        patch.object(
            main.discovery, "discover_and_create_inlets", return_value=[mock_inlet]
        ) as mock_discover,
        patch.object(
            main.main_app_presenter,
            "MainAppPresenter",
            return_value=mock_presenter,
        ) as mock_pres_cls,
        patch.object(main, "schedule_browser_launch") as mock_browser,
        patch.object(main.web_server, "run_server") as mock_run,
    ):
        main.main()

    mock_discover.assert_called_once()
    mock_pres_cls.assert_called_once_with(data_inlets=[mock_inlet])
    mock_browser.assert_called_once()
    mock_run.assert_called_once_with(mock_presenter)


def test_schedule_browser_launch_opens_browser() -> None:
    """Tests schedule_browser_launch schedules a browser open call."""
    with patch.object(main.webbrowser, "open") as mock_open:
        with patch.object(main.threading, "Timer") as mock_timer_cls:
            mock_timer = MagicMock()
            mock_timer_cls.return_value = mock_timer

            main.schedule_browser_launch()

            mock_timer_cls.assert_called_once()
            mock_timer.start.assert_called_once()

            callback = mock_timer_cls.call_args[0][1]
            callback()

    mock_open.assert_called_once_with("http://localhost:8765", new=2, autoraise=True)
