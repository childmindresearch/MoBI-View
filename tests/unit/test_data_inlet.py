"""Unit tests for the DataInlet class in the MoBI_View package."""

from typing import List, Tuple
from unittest.mock import MagicMock

import numpy as np
import pytest
from pylsl.info import StreamInfo
from pylsl.inlet import StreamInlet
from pylsl.util import LostError
from pytest_mock import MockFixture

from MoBI_View.core import config, data_inlet, exceptions


@pytest.fixture
def mock_lsl_info(
    mocker: MockFixture,
) -> Tuple[MagicMock, int, int, List[str], List[str], List[str]]:
    """Creates a mock StreamInfo object.

    The mock StreamInfo includes channel count, labels, types, units, and format.

    Returns:
        A tuple containing mock StreamInfo, channel count, channel format,
        labels, types, and units.
    """
    channel_count = 3
    channel_format = 1
    channel_labels = ["x", "y", "Pupil Size"]
    channel_types = ["Gaze position", "Gaze position", "Pupil diameter"]
    channel_units = ["px", "px", "mm"]

    info = mocker.MagicMock(spec=StreamInfo)
    info.channel_count.return_value = channel_count
    info.channel_format.return_value = channel_format

    info.get_channel_labels.return_value = channel_labels
    info.get_channel_types.return_value = channel_types
    info.get_channel_units.return_value = channel_units

    info.name.return_value = "MockStreamName"
    info.type.return_value = "MockStreamType"

    return (
        info,
        channel_count,
        channel_format,
        channel_labels,
        channel_types,
        channel_units,
    )


@pytest.fixture
def mock_stream_inlet(mocker: MockFixture) -> Tuple[MagicMock, List[float]]:
    """Creates a mock StreamInlet object.

    Returns:
        A tuple containing mock StreamInlet and sample data.
    """
    sample_data = [1.0, 2.0, 3.0]

    inlet = mocker.MagicMock(spec=StreamInlet)
    inlet.pull_sample = mocker.MagicMock(return_value=(sample_data, 0.0))
    return inlet, sample_data


@pytest.fixture
def data_inlet_instance(
    mocker: MockFixture,
    mock_lsl_info: Tuple[MagicMock, int, int, List[str], List[str], List[str]],
    mock_stream_inlet: Tuple[MagicMock, List[float]],
) -> data_inlet.DataInlet:
    """Creates a DataInlet instance with a mock StreamInfo and StreamInlet."""
    info, *_ = mock_lsl_info
    inlet, _ = mock_stream_inlet

    mock_stream = mocker.patch(
        "MoBI_View.core.data_inlet.StreamInlet", return_value=inlet
    )
    mock_stream.return_value.info.return_value = info
    return data_inlet.DataInlet(info)


def test_initialization(
    data_inlet_instance: data_inlet.DataInlet,
    mock_lsl_info: Tuple[MagicMock, int, int, List[str], List[str], List[str]],
) -> None:
    """Tests the initialization of the DataInlet class.

    Verifies that the DataInlet instance correctly initializes channel count, buffer
    shape, channel information, and pointer.

    Args:
        data_inlet_instance: Fixture providing the DataInlet instance.
        mock_lsl_info: Fixture providing mock StreamInfo.
    """
    (
        info,
        channel_count,
        channel_format,
        channel_labels,
        channel_types,
        channel_units,
    ) = mock_lsl_info

    expected_name = info.name.return_value
    expected_type = info.type.return_value

    assert data_inlet_instance.channel_count == channel_count
    assert data_inlet_instance.channel_format == channel_format
    assert data_inlet_instance.ptr == 0
    assert data_inlet_instance.buffers.shape == (
        config.Config.BUFFER_SIZE,
        channel_count,
    )
    assert data_inlet_instance.channel_info["labels"] == channel_labels
    assert data_inlet_instance.channel_info["types"] == channel_types
    assert data_inlet_instance.channel_info["units"] == channel_units
    assert data_inlet_instance.stream_name == expected_name
    assert data_inlet_instance.stream_type == expected_type


def test_get_channel_information(
    data_inlet_instance: data_inlet.DataInlet,
    mock_lsl_info: Tuple[MagicMock, int, int, List[str], List[str], List[str]],
) -> None:
    """Tests the get_channel_information method of DataInlet.

    Ensures that channel information is correctly extracted from the StreamInfo.

    Args:
        data_inlet_instance: Fixture providing the DataInlet instance.
        mock_lsl_info: Fixture providing mock StreamInfo.
    """
    info, _, _, channel_labels, channel_types, channel_units = mock_lsl_info

    channel_info = data_inlet_instance.get_channel_information(info)

    assert channel_info == {
        "labels": channel_labels,
        "types": channel_types,
        "units": channel_units,
    }


def test_get_channel_information_missing(
    data_inlet_instance: data_inlet.DataInlet,
    mock_lsl_info: Tuple[MagicMock, int, int, List[str], List[str], List[str]],
) -> None:
    """Tests get_channel_information when metadata is missing.

    Ensures that default values are used when channel metadata is incomplete,
    missing or is of the wrong length.

    Args:
        data_inlet_instance: Fixture providing the DataInlet instance.
        mock_lsl_info: Fixture providing mock StreamInfo.
    """
    info, channel_count, *_ = mock_lsl_info
    info.get_channel_labels.return_value = [None] * channel_count
    info.get_channel_types.return_value = [None, None]
    info.get_channel_units.return_value = None
    expected_labels = [f"Channel {i + 1}" for i in range(channel_count)]
    expected_types = ["unknown"] * channel_count
    expected_units = ["unknown"] * channel_count

    channel_info = data_inlet_instance.get_channel_information(info)

    assert channel_info == {
        "labels": expected_labels,
        "types": expected_types,
        "units": expected_units,
    }


def test_get_channel_information_partially_missing(
    data_inlet_instance: data_inlet.DataInlet,
    mock_lsl_info: Tuple[MagicMock, int, int, List[str], List[str], List[str]],
) -> None:
    """Tests get_channel_information when metadata lists have incorrect lengths.

    Ensures that default values are used when metadata lists do not match channel_count.

    Args:
        data_inlet_instance: Fixture providing the DataInlet instance.
        mock_lsl_info: Fixture providing mock StreamInfo.
    """
    info, _, _, channel_labels, channel_types, channel_units = mock_lsl_info
    info.get_channel_labels.return_value = [None, channel_labels[1], None]
    info.get_channel_types.return_value = [channel_types[0], None, channel_types[2]]
    info.get_channel_units.return_value = channel_units[:2] + [None]
    expected_labels = ["Channel 1", "y", "Channel 3"]
    expected_types = ["Gaze position", "unknown", "Pupil diameter"]
    expected_units = ["px", "px", "unknown"]

    channel_info = data_inlet_instance.get_channel_information(info)

    assert channel_info == {
        "labels": expected_labels,
        "types": expected_types,
        "units": expected_units,
    }


def test_invalid_channel_count(
    mocker: MockFixture,
    mock_lsl_info: Tuple[MagicMock, int, int, List[str], List[str], List[str]],
) -> None:
    """Tests initialization when channel count is zero.

    Ensures that an InvalidChannelCountError is raised when there are no channels.

    Args:
        mocker: Fixture for mocking objects.
        mock_lsl_info: Fixture providing mock StreamInfo.
    """
    info, *_ = mock_lsl_info
    info.channel_count.return_value = 0

    mock_stream = mocker.patch(
        "MoBI_View.core.data_inlet.StreamInlet", return_value=mocker.MagicMock()
    )
    mock_stream.return_value.info.return_value = info
    with pytest.raises(
        exceptions.InvalidChannelCountError,
        match="Unable to plot data without channels.",
    ):
        data_inlet.DataInlet(info)


@pytest.mark.parametrize("invalid_channel_format", [0, 3, 7])
def test_invalid_channel_format(
    mocker: MockFixture,
    mock_lsl_info: Tuple[MagicMock, int, int, List[str], List[str], List[str]],
    invalid_channel_format: int,
) -> None:
    """Parametrized test for channel_format validation in DataInlet initialization.

    Ensures that the `DataInlet` class raises an `InvalidChannelFormatError` when the
    channel format is non-numeric.

    Args:
        mocker: Fixture for mocking objects.
        mock_lsl_info: Fixture providing mock StreamInfo.
        invalid_channel_format: The channel format to test (Invalid).
    """
    info, *_ = mock_lsl_info
    info.channel_format.return_value = invalid_channel_format

    mock_stream = mocker.patch(
        "MoBI_View.core.data_inlet.StreamInlet", return_value=mocker.MagicMock()
    )
    mock_stream.return_value.info.return_value = info
    with pytest.raises(
        exceptions.InvalidChannelFormatError,
        match="Unable to plot non-numeric data.",
    ):
        data_inlet.DataInlet(info)


@pytest.mark.parametrize("valid_channel_format", [1, 2, 4, 5, 6])
def test_valid_channel_format(
    mocker: MockFixture,
    mock_lsl_info: Tuple[MagicMock, int, int, List[str], List[str], List[str]],
    valid_channel_format: int,
) -> None:
    """Parametrized test for channel_format validation in DataInlet initialization.

    Ensures that the `DataInlet` class initializes correctly when the channel format
    is numeric.

    Args:
        mocker: Fixture for mocking objects.
        mock_lsl_info: Fixture providing mock StreamInfo.
        valid_channel_format: The channel format to test (Valid).
    """
    info, *_ = mock_lsl_info
    info.channel_format.return_value = valid_channel_format

    mock_stream = mocker.patch(
        "MoBI_View.core.data_inlet.StreamInlet", return_value=mocker.MagicMock()
    )
    mock_stream.return_value.info.return_value = info
    inlet = data_inlet.DataInlet(info)

    assert inlet.channel_format == valid_channel_format


def test_pull_sample_success(
    data_inlet_instance: data_inlet.DataInlet,
    mock_stream_inlet: Tuple[MagicMock, List[float]],
) -> None:
    """Tests successfully pulling a sample from the LSL stream.

    Verifies that a sample is correctly pulled and stored in the buffer, and that
    the pointer is incremented.

    Args:
        data_inlet_instance: Fixture providing the DataInlet instance.
        mock_stream_inlet: Fixture providing mock StreamInlet.
    """
    _, sample_data = mock_stream_inlet

    data_inlet_instance.pull_sample()

    assert np.array_equal(data_inlet_instance.buffers[0], sample_data)
    assert data_inlet_instance.ptr == 1


def test_pull_sample_stream_lost(
    data_inlet_instance: data_inlet.DataInlet,
    mock_stream_inlet: Tuple[MagicMock, List[float]],
) -> None:
    """Tests pulling a sample from the LSL stream when the stream is lost.

    Ensures that a StreamLostError is raised if the LSL stream is lost during
    sample pulling.

    Args:
        data_inlet_instance: Fixture providing the DataInlet instance.
        mock_stream_inlet: Fixture providing mock StreamInlet.
    """
    inlet, _ = mock_stream_inlet
    inlet.pull_sample.side_effect = LostError

    with pytest.raises(
        exceptions.StreamLostError, match="Stream source has been lost."
    ):
        data_inlet_instance.pull_sample()
