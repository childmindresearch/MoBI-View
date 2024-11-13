"""Unit tests for the DataInlet class in the MoBI_GUI package."""

from typing import List, Tuple
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from pylsl import LostError, StreamInfo, StreamInlet

from MoBI_GUI.config import Config
from MoBI_GUI.data_inlet import (
    DataInlet,
    InvalidChannelCountError,
    InvalidSampleError,
    StreamLostError,
)


@pytest.fixture
def mock_lsl_info() -> Tuple[MagicMock, int, List[str], List[str], List[str]]:
    """Creates a mock StreamInfo object.

    The mock StreamInfo includes channel count, labels, types, units, and format.

    Returns:
        A tuple containing mock StreamInfo, channel count, labels, types, and units.
    """
    channel_count = 3
    channel_labels = ["x", "y", "Pupil Size"]
    channel_types = ["Gaze position", "Gaze position", "Pupil diameter"]
    channel_units = ["px", "px", "mm"]

    info = MagicMock(spec=StreamInfo)
    info.channel_count.return_value = channel_count
    info.channel_format.return_value = 1  # cf_float32

    info.get_channel_labels.return_value = channel_labels
    info.get_channel_types.return_value = channel_types
    info.get_channel_units.return_value = channel_units

    info.name.return_value = "MockStreamName"
    info.type.return_value = "MockStreamType"

    return info, channel_count, channel_labels, channel_types, channel_units


@pytest.fixture
def mock_stream_inlet() -> Tuple[MagicMock, List[float], float]:
    """Creates a mock StreamInlet object.

    Returns:
        A tuple containing mock StreamInlet, sample data, and timestamp.
    """
    sample_data = [1.0, 2.0, 3.0]
    timestamp = 123.456

    inlet = MagicMock(spec=StreamInlet)
    inlet.pull_sample = MagicMock(return_value=(sample_data, timestamp))
    return inlet, sample_data, timestamp


@pytest.fixture
def data_inlet(
    mock_lsl_info: Tuple[MagicMock, int, List[str], List[str], List[str]],
    mock_stream_inlet: Tuple[MagicMock, List[float], float],
) -> DataInlet:
    """Creates a DataInlet instance with a mock StreamInfo and StreamInlet.

    Args:
        mock_lsl_info: Fixture providing mock StreamInfo.
        mock_stream_inlet: Fixture providing mock StreamInlet.

    Returns:
        An instance of DataInlet with mocked dependencies.
    """
    info, *_ = mock_lsl_info
    inlet, *_ = mock_stream_inlet

    with patch("MoBI_GUI.data_inlet.StreamInlet", return_value=inlet):
        return DataInlet(info=info)


def test_initialization(
    data_inlet: DataInlet,
    mock_lsl_info: Tuple[MagicMock, int, List[str], List[str], List[str]],
) -> None:
    """Tests the initialization of the DataInlet class.

    Verifies that the DataInlet instance correctly initializes channel count, buffer
    shape, channel information, and pointer.

    Args:
        data_inlet: Fixture providing the DataInlet instance.
        mock_lsl_info: Fixture providing mock StreamInfo.
    """
    info, channel_count, channel_labels, channel_types, channel_units = mock_lsl_info

    expected_name = info.name.return_value
    expected_type = info.type.return_value

    assert data_inlet.channel_count == channel_count
    assert data_inlet.ptr == 0
    assert data_inlet.buffers.shape == (Config.BUFFER_SIZE, channel_count)
    assert data_inlet.channel_info["labels"] == channel_labels
    assert data_inlet.channel_info["types"] == channel_types
    assert data_inlet.channel_info["units"] == channel_units
    assert data_inlet.stream_name == expected_name
    assert data_inlet.stream_type == expected_type


def test_get_channel_information(
    data_inlet: DataInlet,
    mock_lsl_info: Tuple[MagicMock, int, List[str], List[str], List[str]],
) -> None:
    """Tests the get_channel_information method of DataInlet.

    Ensures that channel information is correctly extracted from the StreamInfo.

    Args:
        data_inlet: Fixture providing the DataInlet instance.
        mock_lsl_info: Fixture providing mock StreamInfo.
    """
    info, _, channel_labels, channel_types, channel_units = mock_lsl_info

    channel_info = data_inlet.get_channel_information(info)

    assert channel_info == {
        "labels": channel_labels,
        "types": channel_types,
        "units": channel_units,
    }


def test_get_channel_information_missing(
    data_inlet: DataInlet,
    mock_lsl_info: Tuple[MagicMock, int, List[str], List[str], List[str]],
) -> None:
    """Tests get_channel_information when metadata is missing.

    Ensures that default values are used when channel metadata is incomplete,
    missing or is of the wrong length.

    Args:
        data_inlet: Fixture providing the DataInlet instance.
        mock_lsl_info: Fixture providing mock StreamInfo.
    """
    info, channel_count, *_ = mock_lsl_info
    info.get_channel_labels.return_value = [None] * channel_count
    info.get_channel_types.return_value = [None, None]
    info.get_channel_units.return_value = None
    expected_labels = [f"Channel {i+1}" for i in range(channel_count)]
    expected_types = ["unknown"] * channel_count
    expected_units = ["unknown"] * channel_count

    channel_info = data_inlet.get_channel_information(info)

    assert channel_info == {
        "labels": expected_labels,
        "types": expected_types,
        "units": expected_units,
    }


def test_get_channel_information_partially_missing(
    data_inlet: DataInlet,
    mock_lsl_info: Tuple[MagicMock, int, List[str], List[str], List[str]],
) -> None:
    """Tests get_channel_information when metadata lists have incorrect lengths.

    Ensures that default values are used when metadata lists do not match channel_count.

    Args:
        data_inlet: Fixture providing the DataInlet instance.
        mock_lsl_info: Fixture providing mock StreamInfo.
    """
    info, _, channel_labels, channel_types, channel_units = mock_lsl_info
    info.get_channel_labels.return_value = [None, channel_labels[1], None]
    info.get_channel_types.return_value = [channel_types[0], None, channel_types[2]]
    info.get_channel_units.return_value = channel_units[:2] + [None]
    expected_labels = ["Channel 1", "y", "Channel 3"]
    expected_types = ["Gaze position", "unknown", "Pupil diameter"]
    expected_units = ["px", "px", "unknown"]

    channel_info = data_inlet.get_channel_information(info)

    assert channel_info == {
        "labels": expected_labels,
        "types": expected_types,
        "units": expected_units,
    }


def test_invalid_channel_count(
    mock_lsl_info: Tuple[MagicMock, int, List[str], List[str], List[str]],
) -> None:
    """Tests initialization when channel count is zero.

    Ensures that an InvalidChannelCountError is raised when there are no channels.

    Args:
        mock_lsl_info: Fixture providing mock StreamInfo.
    """
    info, *_ = mock_lsl_info
    info.channel_count.return_value = 0

    with patch("MoBI_GUI.data_inlet.StreamInlet", return_value=MagicMock()):
        with pytest.raises(
            InvalidChannelCountError, match="Unable to plot data without channels."
        ):
            DataInlet(info=info)


@pytest.mark.parametrize(
    "channel_format, should_raise",
    [
        (0, True),  # Undefined format (invalid)
        (1, False),  # cf_float32
        (2, False),  # cf_double64
        (3, True),  # cf_string (invalid)
        (4, False),  # cf_int32
        (5, False),  # cf_int16
        (6, False),  # cf_int8
        (7, False),  # cf_int64
    ],
)
def test_invalid_sample_error_(
    mock_lsl_info: Tuple[MagicMock, int, List[str], List[str], List[str]],
    channel_format: int,
    should_raise: bool,
) -> None:
    """Parametrized test for channel_format validation in DataInlet initialization.
    
    Ensures that the `DataInlet` class raises an `InvalidSampleError` when the
    channel format is non-numeric
    
    Args:
        mock_lsl_info: Fixture providing mock StreamInfo.
        channel_format: The channel format to test.
        should_raise: Whether the test should expect an exception.
    """
    info, *_ = mock_lsl_info
    info.channel_format.return_value = channel_format

    with patch("MoBI_GUI.data_inlet.StreamInlet", return_value=MagicMock()):
        if should_raise:
            with pytest.raises(
                InvalidSampleError, match="Unable to plot non-numeric data."
            ):
                DataInlet(info=info)


def test_pull_sample_success(
    data_inlet: DataInlet, mock_stream_inlet: Tuple[MagicMock, List[float], float]
) -> None:
    """Tests successfully pulling a sample from the LSL stream.

    Verifies that a sample is correctly pulled and stored in the buffer, and that
    the pointer is incremented.

    Args:
        data_inlet: Fixture providing the DataInlet instance.
        mock_stream_inlet: Fixture providing mock StreamInlet.
    """
    _, sample_data, _ = mock_stream_inlet

    data_inlet.pull_sample()

    assert np.array_equal(data_inlet.buffers[0], sample_data)
    assert data_inlet.ptr == 1


def test_pull_sample_stream_lost(
    data_inlet: DataInlet, mock_stream_inlet: Tuple[MagicMock, List[float], float]
) -> None:
    """Tests pulling a sample from the LSL stream when the stream is lost.

    Ensures that a StreamLostError is raised if the LSL stream is lost during
    sample pulling.

    Args:
        data_inlet: Fixture providing the DataInlet instance.
        mock_stream_inlet: Fixture providing mock StreamInlet.
    """
    inlet, *_ = mock_stream_inlet
    inlet.pull_sample.side_effect = LostError

    with pytest.raises(StreamLostError, match="Stream source has been lost."):
        data_inlet.pull_sample()
