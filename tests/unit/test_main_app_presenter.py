"""Unit tests for MainAppPresenter."""

from typing import List
from unittest.mock import MagicMock

import pytest

from MoBI_View.core import data_inlet, exceptions
from MoBI_View.presenters import main_app_presenter


@pytest.fixture
def mock_inlet() -> MagicMock:
    """Return a mock data inlet."""
    mock = MagicMock()
    mock.stream_name = "Stream1"
    mock.stream_type = "EEG"
    mock.channel_info = {
        "labels": ["Channel1", "Channel2"],
        "units": ["microvolts", "microvolts"],
    }
    mock.pull_chunk.return_value = ([], [])
    return mock


def test_presenter_initialization(mock_inlet: MagicMock) -> None:
    """Tests MainAppPresenter initializes with given data inlets."""
    presenter = main_app_presenter.MainAppPresenter(data_inlets=[mock_inlet])
    assert presenter.data_inlets == [mock_inlet]


def test_poll_data_success(mock_inlet: MagicMock) -> None:
    """Tests every sample and its original timestamp are forwarded with metadata."""
    mock_inlet.pull_chunk.return_value = (
        [[1.0, 2.0], [3.0, 4.0]],
        [10.0, 10.004],
    )
    presenter = main_app_presenter.MainAppPresenter(data_inlets=[mock_inlet])

    expected_plot_data = [
        {
            "stream_name": "Stream1",
            "stream_type": "EEG",
            "samples": [[1.0, 2.0], [3.0, 4.0]],
            "timestamps": [10.0, 10.004],
            "channel_labels": ["Channel1", "Channel2"],
            "channel_units": ["microvolts", "microvolts"],
        }
    ]

    results = presenter.poll_data()

    mock_inlet.pull_chunk.assert_called_once()
    assert results == expected_plot_data


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


def test_on_data_updated(mock_inlet: MagicMock) -> None:
    """Tests on_data_updated returns correct plot data."""
    presenter = main_app_presenter.MainAppPresenter(data_inlets=[mock_inlet])
    samples = [[1.0, 2.0], [3.0, 4.0]]
    timestamps = [10.0, 10.004]
    channel_labels = ["Channel1", "Channel2"]
    channel_units = ["microvolts", "microvolts"]

    expected_plot_data = {
        "stream_name": "Stream1",
        "stream_type": "EEG",
        "samples": [[1.0, 2.0], [3.0, 4.0]],
        "timestamps": [10.0, 10.004],
        "channel_labels": ["Channel1", "Channel2"],
        "channel_units": ["microvolts", "microvolts"],
    }

    result = presenter.on_data_updated(
        "Stream1", "EEG", samples, timestamps, channel_labels, channel_units
    )

    assert result == expected_plot_data


def test_on_data_updated_empty_sample(mock_inlet: MagicMock) -> None:
    """Tests on_data_updated handles empty samples."""
    presenter = main_app_presenter.MainAppPresenter(data_inlets=[mock_inlet])
    samples: List[List[data_inlet.SampleValue]] = []
    timestamps: List[float] = []
    channel_labels: List[str] = []
    channel_units: List[str] = []
    expected_plot_data = {
        "stream_name": "Stream1",
        "stream_type": "EEG",
        "samples": [],
        "timestamps": [],
        "channel_labels": [],
        "channel_units": [],
    }

    result = presenter.on_data_updated(
        "Stream1", "EEG", samples, timestamps, channel_labels, channel_units
    )

    assert result == expected_plot_data


def test_poll_data_multiple_inlets() -> None:
    """Tests poll_data with multiple inlets returns data from all active inlets."""
    mock_inlet1 = MagicMock()
    mock_inlet1.stream_name = "Stream1"
    mock_inlet1.stream_type = "EEG"
    mock_inlet1.channel_info = {"labels": ["Ch1"], "units": ["microvolts"]}
    mock_inlet1.pull_chunk.return_value = ([[5.0]], [1.0])

    mock_inlet2 = MagicMock()
    mock_inlet2.stream_name = "Stream2"
    mock_inlet2.stream_type = "Gaze"
    mock_inlet2.channel_info = {"labels": ["Ch2"], "units": ["deg"]}
    mock_inlet2.pull_chunk.return_value = ([[10.0]], [2.0])

    presenter = main_app_presenter.MainAppPresenter(
        data_inlets=[mock_inlet1, mock_inlet2]
    )

    expected_plot_data = [
        {
            "stream_name": "Stream1",
            "stream_type": "EEG",
            "samples": [[5.0]],
            "timestamps": [1.0],
            "channel_labels": ["Ch1"],
            "channel_units": ["microvolts"],
        },
        {
            "stream_name": "Stream2",
            "stream_type": "Gaze",
            "samples": [[10.0]],
            "timestamps": [2.0],
            "channel_labels": ["Ch2"],
            "channel_units": ["deg"],
        },
    ]

    results = presenter.poll_data()

    assert results == expected_plot_data


@pytest.mark.parametrize(
    "samples",
    [[["marker"], ["experiment start"]], [["recording start"], ["marker"]]],
)
def test_poll_data_marker_samples(
    mock_inlet: MagicMock, samples: List[List[str]]
) -> None:
    """Tests marker chunks pass through the presenter without numeric coercion."""
    mock_inlet.stream_name = "AudioMarkerStream"
    mock_inlet.stream_type = "Markers"
    mock_inlet.channel_info = {"labels": ["Marker"], "units": ["label"]}
    mock_inlet.pull_chunk.return_value = (samples, [1.0, 6.0])
    presenter = main_app_presenter.MainAppPresenter(data_inlets=[mock_inlet])

    expected_plot_data = [
        {
            "stream_name": "AudioMarkerStream",
            "stream_type": "Markers",
            "samples": samples,
            "timestamps": [1.0, 6.0],
            "channel_labels": ["Marker"],
            "channel_units": ["label"],
        }
    ]

    results = presenter.poll_data()

    assert results == expected_plot_data


def test_poll_data_propagates_invalid_timestamps(mock_inlet: MagicMock) -> None:
    """Tests timestamp validation failures are passed through unchanged."""
    error = ValueError("timestamps must be finite and strictly increasing")
    mock_inlet.pull_chunk.side_effect = error
    presenter = main_app_presenter.MainAppPresenter([mock_inlet])

    with pytest.raises(ValueError) as raised:
        presenter.poll_data()

    assert raised.value is error


def test_on_data_updated_preserves_custom_stream_type(mock_inlet: MagicMock) -> None:
    """Tests LSL source-defined content types do not require an enum member."""
    presenter = main_app_presenter.MainAppPresenter([mock_inlet])
    expected_plot_data = {
        "stream_name": "Device1",
        "stream_type": "VendorCustomSignal",
        "samples": [[1, 2.5]],
        "timestamps": [10.0],
        "channel_labels": ["A", "B"],
        "channel_units": ["count", "V"],
    }

    result = presenter.on_data_updated(
        "Device1", "VendorCustomSignal", [[1, 2.5]], [10.0], ["A", "B"], ["count", "V"]
    )

    assert result == expected_plot_data


def test_poll_data_does_not_replay_previous_chunk(mock_inlet: MagicMock) -> None:
    """Tests empty polls do not emit the previous chunk again."""
    mock_inlet.pull_chunk.side_effect = [([[1.0, 2.0]], [10.0]), ([], [])]
    presenter = main_app_presenter.MainAppPresenter(data_inlets=[mock_inlet])

    first_result = presenter.poll_data()
    second_result = presenter.poll_data()

    assert len(first_result) == 1
    assert second_result == []


def test_poll_data_skips_empty_inlet(mock_inlet: MagicMock) -> None:
    """Tests an empty inlet does not prevent a subsequent active inlet from emitting."""
    empty_inlet = MagicMock()
    empty_inlet.pull_chunk.return_value = ([], [])
    mock_inlet.pull_chunk.return_value = ([[1.0, 2.0]], [10.0])
    presenter = main_app_presenter.MainAppPresenter([empty_inlet, mock_inlet])

    results = presenter.poll_data()

    assert len(results) == 1
    assert results[0]["stream_name"] == "Stream1"
    empty_inlet.pull_chunk.assert_called_once()
    mock_inlet.pull_chunk.assert_called_once()
