"""Unit tests for the DataInlet class in the MoBI_GUI package."""

from typing import List, Tuple
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from pylsl import LostError, StreamInfo, StreamInlet

from MoBI_GUI.config import Config
from MoBI_GUI.data_inlet import DataInlet, StreamLostError


@pytest.fixture
def mock_lsl_info() -> Tuple[MagicMock, int, List[str], List[str], List[str]]:
    """Fixture to create a mock StreamInfo.

    Returns:
        Tuple containing mock StreamInfo, channel count, labels, types, and units.
    """
    channel_count = 3
    channel_labels = ["x", "y", "Pupil Size"]
    channel_types = ["Gaze position", "Gaze position", "Pupil diameter"]
    channel_units = ["px", "px", "mm"]

    info = MagicMock(spec=StreamInfo)
    info.channel_count.return_value = channel_count
    info.get_channel_labels.return_value = channel_labels
    info.get_channel_types.return_value = channel_types
    info.get_channel_units.return_value = channel_units
    info.name = "TestStream"
    return info, channel_count, channel_labels, channel_types, channel_units


@pytest.fixture
def mock_stream_inlet() -> Tuple[MagicMock, List[float], float]:
    """Fixture to create a mock StreamInlet.

    Returns:
        Tuple containing mock StreamInlet, sample data, and timestamp.
    """
    sample_data = [1.0, 2.0, 3.0]
    timestamp = 123.456
    inlet = MagicMock(spec=StreamInlet)
    inlet.pull_sample = MagicMock(return_value=(sample_data, timestamp))
    inlet.info.return_value = MagicMock()
    return inlet, sample_data, timestamp


@pytest.fixture
def data_inlet(
    mock_lsl_info: Tuple[MagicMock, int, List[str], List[str], List[str]],
    mock_stream_inlet: Tuple[MagicMock, List[float], float],
) -> DataInlet:
    """Fixture to create a DataInlet instance with a mock StreamInfo and StreamInlet.

    Args:
        mock_lsl_info: Fixture providing mock StreamInfo.
        mock_stream_inlet: Fixture providing mock StreamInlet.

    Returns:
        DataInlet instance with mocked dependencies.
    """
    info, _, _, _, _ = mock_lsl_info
    inlet, _, _ = mock_stream_inlet
    with patch("MoBI_GUI.data_inlet.StreamInlet", return_value=inlet):
        return DataInlet(info=info)


def test_get_channel_information(
    data_inlet: DataInlet,
    mock_lsl_info: Tuple[MagicMock, int, List[str], List[str], List[str]],
) -> None:
    """Test the get_channel_information method of DataInlet.

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


def test_get_channel_information_no_metadata(
    mock_lsl_info: Tuple[MagicMock, int, List[str], List[str], List[str]],
) -> None:
    """Test get_channel_information when metadata is missing.

    Args:
        mock_lsl_info: Fixture providing mock StreamInfo.
    """
    info, channel_count, _, _, _ = mock_lsl_info
    info.get_channel_labels.return_value = None
    info.get_channel_types.return_value = None
    info.get_channel_units.return_value = None
    with patch("MoBI_GUI.data_inlet.StreamInlet", return_value=MagicMock()):
        inlet = DataInlet(info=info)

    channel_info = inlet.get_channel_information(info)

    assert channel_info == {
        "labels": [f"Channel {i+1}" for i in range(channel_count)],
        "types": ["unknown"] * channel_count,
        "units": ["unknown"] * channel_count,
    }


def test_pull_sample_success(
    data_inlet: DataInlet, mock_stream_inlet: Tuple[MagicMock, List[float], float]
) -> None:
    """Test pulling a sample from the LSL stream successfully.

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
    """Test pulling a sample from the LSL stream when the stream is lost.

    Args:
        data_inlet: Fixture providing the DataInlet instance.
        mock_stream_inlet: Fixture providing mock StreamInlet.
    """
    inlet, _, _ = mock_stream_inlet
    inlet.pull_sample.side_effect = LostError

    with pytest.raises(StreamLostError, match="Stream source has been lost."):
        data_inlet.pull_sample()


def test_initialization(
    data_inlet: DataInlet,
    mock_lsl_info: Tuple[MagicMock, int, List[str], List[str], List[str]],
) -> None:
    """Test initialization of DataInlet.

    Args:
        data_inlet: Fixture providing the DataInlet instance.
        mock_lsl_info: Fixture providing mock StreamInfo.
    """
    _, channel_count, channel_labels, _, _ = mock_lsl_info

    assert data_inlet.channel_count == channel_count
    assert data_inlet.ptr == 0
    assert data_inlet.buffers.shape == (Config.BUFFER_SIZE, channel_count)
    assert data_inlet.channel_names == channel_labels
