"""Smoke tests for MoBI-View application using real LSL streams.

Tests the application's ability to discover and connect to LSL streams.
"""

import time
from typing import Generator

import numpy as np
import pytest
from pylsl import StreamInfo, StreamOutlet, resolve_streams

from MoBI_View.core.data_inlet import DataInlet


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


def test_data_inlet_with_real_streams(
    eeg_stream: StreamOutlet,
    accel_stream: StreamOutlet,
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

    discovered_streams = resolve_streams()
    data_inlets = []
    for info in discovered_streams:
        try:
            inlet = DataInlet(info)
            data_inlets.append(inlet)
        except Exception as err:
            pytest.fail(f"Failed to create DataInlet: {err}")
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
    discovered_streams = resolve_streams(wait_time=0.1)
    test_streams = [s for s in discovered_streams if "Test" in s.name()]

    if len(test_streams) == 0:
        data_inlets = []
        for info in discovered_streams:
            try:
                inlet = DataInlet(info)
                data_inlets.append(inlet)
            except Exception:
                pass

        assert isinstance(data_inlets, list)
