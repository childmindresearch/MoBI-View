"""Unit tests for MainAppPresenter."""

from typing import Any
from unittest.mock import MagicMock

import pytest

from MoBI_View.core import exceptions
from MoBI_View.presenters import main_app_presenter


@pytest.fixture
def mock_inlet() -> MagicMock:
    """Return a mock data inlet."""
    mock = MagicMock()
    mock.stream_name = "Stream1"
    mock.stream_type = "EEG"
    mock.channel_info = {
        "labels": ["Channel1", "Channel2"],
        "units": ["uV", "uV"],
    }
    mock.pull_chunk.return_value = ([], [])
    return mock


def test_presenter_initialization(mock_inlet: MagicMock) -> None:
    """Tests MainAppPresenter initializes with given data inlets."""
    presenter = main_app_presenter.MainAppPresenter(data_inlets=[mock_inlet])
    assert presenter.data_inlets == [mock_inlet]


def test_poll_data_success(mock_inlet: MagicMock) -> None:
    """Tests poll_data with successful data retrieval returns correct data."""
    mock_inlet.pull_chunk.return_value = ([[1.0, 2.0], [3.0, 4.0]], [10.0, 10.004])
    presenter = main_app_presenter.MainAppPresenter(data_inlets=[mock_inlet])

    results = presenter.poll_data()

    mock_inlet.pull_chunk.assert_called_once()
    assert len(results) == 1
    assert results[0]["stream_name"] == "Stream1"
    assert results[0]["stream_type"] == "EEG"
    assert results[0]["samples"] == [[1.0, 2.0], [3.0, 4.0]]
    assert results[0]["timestamps"] == [10.0, 10.004]
    assert results[0]["channel_labels"] == ["Channel1", "Channel2"]
    assert results[0]["channel_units"] == ["uV", "uV"]


def test_poll_data_no_samples(mock_inlet: MagicMock) -> None:
    """Tests poll_data when no new samples are available returns empty list."""
    presenter = main_app_presenter.MainAppPresenter(data_inlets=[mock_inlet])

    results = presenter.poll_data()

    mock_inlet.pull_chunk.assert_called_once()
    assert len(results) == 0


def test_poll_data_stream_lost(mock_inlet: MagicMock) -> None:
    """Tests poll_data propagates StreamLostError."""
    mock_inlet.pull_chunk.side_effect = exceptions.StreamLostError("Stream1")
    presenter = main_app_presenter.MainAppPresenter(data_inlets=[mock_inlet])

    with pytest.raises(exceptions.StreamLostError):
        presenter.poll_data()


def test_poll_data_invalid_channel_count(mock_inlet: MagicMock) -> None:
    """Tests poll_data propagates InvalidChannelCountError."""
    error_msg = "Invalid channel count"
    mock_inlet.pull_chunk.side_effect = exceptions.InvalidChannelCountError(
        error_msg, 2, 3
    )
    presenter = main_app_presenter.MainAppPresenter(data_inlets=[mock_inlet])

    with pytest.raises(exceptions.InvalidChannelCountError):
        presenter.poll_data()


def test_poll_data_invalid_channel_format(mock_inlet: MagicMock) -> None:
    """Tests poll_data propagates InvalidChannelFormatError."""
    error_msg = "Invalid channel format"
    mock_inlet.pull_chunk.side_effect = exceptions.InvalidChannelFormatError(
        error_msg, "float", "string"
    )
    presenter = main_app_presenter.MainAppPresenter(data_inlets=[mock_inlet])

    with pytest.raises(exceptions.InvalidChannelFormatError):
        presenter.poll_data()


def test_poll_data_unexpected_exception(mock_inlet: MagicMock) -> None:
    """Tests poll_data propagates unexpected exceptions."""
    mock_inlet.pull_chunk.side_effect = RuntimeError("Unexpected error")
    presenter = main_app_presenter.MainAppPresenter(data_inlets=[mock_inlet])

    with pytest.raises(RuntimeError):
        presenter.poll_data()


def test_poll_data_marker_samples(mock_inlet: MagicMock) -> None:
    """Tests poll_data forwards string marker samples unchanged."""
    mock_inlet.stream_name = "AudioMarkerStream"
    mock_inlet.stream_type = "Markers"
    mock_inlet.channel_info = {"labels": ["Marker"], "units": ["label"]}
    mock_inlet.pull_chunk.return_value = ([["beep"], ["speech_start"]], [1.0, 1.1])
    presenter = main_app_presenter.MainAppPresenter(data_inlets=[mock_inlet])

    results = presenter.poll_data()

    assert results[0]["samples"] == [["beep"], ["speech_start"]]
    assert results[0]["stream_type"] == "Markers"


def test_on_data_updated(mock_inlet: MagicMock) -> None:
    """Tests on_data_updated returns correct plot data."""
    presenter = main_app_presenter.MainAppPresenter(data_inlets=[mock_inlet])

    result = presenter.on_data_updated(
        "Stream1", "EEG", [[1.0, 2.0]], [7.5], ["Channel1", "Channel2"], ["uV", "uV"]
    )

    expected_plot_data = {
        "stream_name": "Stream1",
        "stream_type": "EEG",
        "samples": [[1.0, 2.0]],
        "timestamps": [7.5],
        "channel_labels": ["Channel1", "Channel2"],
        "channel_units": ["uV", "uV"],
    }
    assert result == expected_plot_data


def test_on_data_updated_empty_sample(mock_inlet: MagicMock) -> None:
    """Tests on_data_updated handles empty samples."""
    presenter = main_app_presenter.MainAppPresenter(data_inlets=[mock_inlet])
    channel_labels: list[Any] = []
    channel_units: list[Any] = []
    expected_plot_data = {
        "stream_name": "Stream1",
        "stream_type": "EEG",
        "samples": [],
        "timestamps": [],
        "channel_labels": [],
        "channel_units": [],
    }

    result = presenter.on_data_updated(
        "Stream1", "EEG", [], [], channel_labels, channel_units
    )

    assert result == expected_plot_data


def test_poll_data_multiple_inlets() -> None:
    """Tests poll_data with multiple inlets returns data from all active inlets."""
    mock_inlet1 = MagicMock()
    mock_inlet1.stream_name = "Stream1"
    mock_inlet1.stream_type = "EEG"
    mock_inlet1.channel_info = {"labels": ["Ch1"], "units": ["uV"]}
    mock_inlet1.pull_chunk.return_value = ([[5.0]], [1.0])

    mock_inlet2 = MagicMock()
    mock_inlet2.stream_name = "Stream2"
    mock_inlet2.stream_type = "Gaze"
    mock_inlet2.channel_info = {"labels": ["Ch2"], "units": ["deg"]}
    mock_inlet2.pull_chunk.return_value = ([[10.0]], [2.0])

    presenter = main_app_presenter.MainAppPresenter(
        data_inlets=[mock_inlet1, mock_inlet2]
    )
    results = presenter.poll_data()

    assert len(results) == 2
    assert results[0]["stream_name"] == "Stream1"
    assert results[0]["samples"] == [[5.0]]
    assert results[1]["stream_name"] == "Stream2"
    assert results[1]["samples"] == [[10.0]]
