"""Unit tests for MainAppPresenter."""

from typing import Any
from unittest.mock import MagicMock

import numpy as np
import pytest

from MoBI_View.core import config, exceptions
from MoBI_View.presenters import main_app_presenter


@pytest.fixture
def mock_inlet() -> MagicMock:
    """Return a mock data inlet."""
    mock = MagicMock()
    mock.stream_name = "Stream1"
    mock.channel_info = {"labels": ["Channel1", "Channel2"]}
    mock.ptr = 0
    mock.buffers = np.zeros((config.Config.BUFFER_SIZE, 2))
    return mock


def test_presenter_initialization(mock_inlet: MagicMock) -> None:
    """Tests MainAppPresenter initializes with given data inlets."""
    presenter = main_app_presenter.MainAppPresenter(data_inlets=[mock_inlet])
    assert presenter.channel_visibility == {
        "Stream1:Channel1": True,
        "Stream1:Channel2": True,
    }
    assert presenter.data_inlets == [mock_inlet]


def test_poll_data_success(mock_inlet: MagicMock) -> None:
    """Tests poll_data with successful data retrieval returns correct data."""
    mock_inlet.ptr = 1
    mock_inlet.buffers[0] = np.array([1.0, 2.0])
    presenter = main_app_presenter.MainAppPresenter(data_inlets=[mock_inlet])

    results = presenter.poll_data()

    mock_inlet.pull_sample.assert_called_once()
    assert len(results) == 1
    assert results[0]["stream_name"] == "Stream1"
    assert results[0]["data"] == [1.0, 2.0]
    assert results[0]["channel_labels"] == ["Channel1", "Channel2"]


def test_poll_data_no_samples(mock_inlet: MagicMock) -> None:
    """Tests poll_data when no new samples are available returns empty list."""
    mock_inlet.ptr = 0
    presenter = main_app_presenter.MainAppPresenter(data_inlets=[mock_inlet])

    results = presenter.poll_data()

    mock_inlet.pull_sample.assert_called_once()
    assert len(results) == 0


def test_poll_data_stream_lost(mock_inlet: MagicMock) -> None:
    """Tests poll_data propagates StreamLostError."""
    mock_inlet.pull_sample.side_effect = exceptions.StreamLostError("Stream1")
    presenter = main_app_presenter.MainAppPresenter(data_inlets=[mock_inlet])

    with pytest.raises(exceptions.StreamLostError):
        presenter.poll_data()


def test_poll_data_invalid_channel_count(mock_inlet: MagicMock) -> None:
    """Tests poll_data propagates InvalidChannelCountError."""
    error_msg = "Invalid channel count"
    mock_inlet.pull_sample.side_effect = exceptions.InvalidChannelCountError(
        error_msg, 2, 3
    )
    presenter = main_app_presenter.MainAppPresenter(data_inlets=[mock_inlet])

    with pytest.raises(exceptions.InvalidChannelCountError):
        presenter.poll_data()


def test_poll_data_invalid_channel_format(mock_inlet: MagicMock) -> None:
    """Tests poll_data propagates InvalidChannelFormatError."""
    error_msg = "Invalid channel format"
    mock_inlet.pull_sample.side_effect = exceptions.InvalidChannelFormatError(
        error_msg, "float", "string"
    )
    presenter = main_app_presenter.MainAppPresenter(data_inlets=[mock_inlet])

    with pytest.raises(exceptions.InvalidChannelFormatError):
        presenter.poll_data()


def test_poll_data_unexpected_exception(mock_inlet: MagicMock) -> None:
    """Tests poll_data propagates unexpected exceptions."""
    mock_inlet.pull_sample.side_effect = RuntimeError("Unexpected error")
    presenter = main_app_presenter.MainAppPresenter(data_inlets=[mock_inlet])

    with pytest.raises(RuntimeError):
        presenter.poll_data()


def test_update_channel_visibility(mock_inlet: MagicMock) -> None:
    """Tests update_channel_visibility updates visibility state."""
    presenter = main_app_presenter.MainAppPresenter(data_inlets=[mock_inlet])

    presenter.update_channel_visibility("Stream1:Channel1", False)

    assert presenter.channel_visibility["Stream1:Channel1"] is False


def test_on_data_updated(mock_inlet: MagicMock) -> None:
    """Tests on_data_updated returns correct plot data."""
    presenter = main_app_presenter.MainAppPresenter(data_inlets=[mock_inlet])
    sample = np.array([1.0, 2.0])
    channel_labels = ["Channel1", "Channel2"]

    result = presenter.on_data_updated("Stream1", sample, channel_labels)

    expected_plot_data = {
        "stream_name": "Stream1",
        "data": [1.0, 2.0],
        "channel_labels": ["Channel1", "Channel2"],
    }
    assert result == expected_plot_data


def test_on_data_updated_empty_sample(mock_inlet: MagicMock) -> None:
    """Tests on_data_updated handles empty samples."""
    presenter = main_app_presenter.MainAppPresenter(data_inlets=[mock_inlet])
    sample = np.array([])
    channel_labels: list[Any] = []

    result = presenter.on_data_updated("Stream1", sample, channel_labels)

    expected_plot_data = {
        "stream_name": "Stream1",
        "data": [],
        "channel_labels": [],
    }
    assert result == expected_plot_data


def test_poll_data_multiple_inlets() -> None:
    """Tests poll_data with multiple inlets returns data from all active inlets."""
    mock_inlet1 = MagicMock()
    mock_inlet1.stream_name = "Stream1"
    mock_inlet1.channel_info = {"labels": ["Ch1"]}
    mock_inlet1.ptr = 1
    mock_inlet1.buffers = np.zeros((config.Config.BUFFER_SIZE, 1))
    mock_inlet1.buffers[0] = np.array([5.0])

    mock_inlet2 = MagicMock()
    mock_inlet2.stream_name = "Stream2"
    mock_inlet2.channel_info = {"labels": ["Ch2"]}
    mock_inlet2.ptr = 1
    mock_inlet2.buffers = np.zeros((config.Config.BUFFER_SIZE, 1))
    mock_inlet2.buffers[0] = np.array([10.0])

    presenter = main_app_presenter.MainAppPresenter(
        data_inlets=[mock_inlet1, mock_inlet2]
    )
    results = presenter.poll_data()

    assert len(results) == 2
    assert results[0]["stream_name"] == "Stream1"
    assert results[0]["data"] == [5.0]
    assert results[1]["stream_name"] == "Stream2"
    assert results[1]["data"] == [10.0]
