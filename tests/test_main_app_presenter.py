"""Unit tests for the MainAppPresenter class in the MoBI_GUI package."""

from unittest.mock import MagicMock, call, patch

import numpy as np
import pytest

from MoBI_GUI import data_inlet, exceptions, presenters, views


@pytest.fixture
def mock_view() -> MagicMock:
    """Creates a mock instance of IMainAppView."""
    view_mock = MagicMock(spec=views.interfaces.IMainAppView)
    return view_mock


@pytest.fixture
def mock_data_inlet1() -> MagicMock:
    """Creates the first mock instance of DataInlet."""
    inlet_mock = MagicMock(spec=data_inlet.DataInlet)
    inlet_mock.stream_name = "Stream1"
    inlet_mock.channel_info = {"labels": ["Channel1", "Channel2"]}
    inlet_mock.buffers = np.array([[0.1, 0.2], [0.3, 0.4]])
    inlet_mock.ptr = 2
    return inlet_mock


@pytest.fixture
def mock_data_inlet2() -> MagicMock:
    """Creates the second mock instance of DataInlet."""
    inlet_mock = MagicMock(spec=data_inlet.DataInlet)
    inlet_mock.stream_name = "Stream2"
    inlet_mock.channel_info = {"labels": ["ChannelA", "ChannelB"]}
    inlet_mock.buffers = np.array([[1.1, 1.2], [1.3, 1.4]])
    inlet_mock.ptr = 2
    return inlet_mock


@pytest.fixture
def presenter(
    mock_view: MagicMock, mock_data_inlet1: MagicMock, mock_data_inlet2: MagicMock
) -> presenters.main_app_presenter.MainAppPresenter:
    """Creates an instance of MainAppPresenter with mocked dependencies."""
    with patch("PyQt5.QtCore.QTimer") as MockTimer:
        mock_timer_instance = MagicMock()
        MockTimer.return_value = mock_timer_instance
        presenter_instance = presenters.main_app_presenter.MainAppPresenter(
            view=mock_view, data_inlets=[mock_data_inlet1, mock_data_inlet2]
        )
    return presenter_instance


def test_presenter_initialization(
    presenter: presenters.main_app_presenter.MainAppPresenter, mock_view: MagicMock
) -> None:
    """Tests the initialization of the MainAppPresenter class.

    Args:
        presenter: An instance of MainAppPresenter.
        mock_view: A mocked instance of IMainAppView.
    """
    expected_visibility = {
        "Stream1:Channel1": True,
        "Stream1:Channel2": True,
        "Stream2:ChannelA": True,
        "Stream2:ChannelB": True,
    }

    assert presenter.channel_visibility == expected_visibility

    expected_calls = [
        call("Stream1:Channel1", True),
        call("Stream1:Channel2", True),
        call("Stream2:ChannelA", True),
        call("Stream2:ChannelB", True),
    ]
    mock_view.toggle_channel_visibility.assert_has_calls(expected_calls)


def test_poll_data_success(
    presenter: presenters.main_app_presenter.MainAppPresenter,
    mock_view: MagicMock,
    mock_data_inlet1: MagicMock,
    mock_data_inlet2: MagicMock,
) -> None:
    """Tests the poll_data method when data is successfully pulled from DataInlets.

    Args:
        presenter: An instance of MainAppPresenter.
        mock_view: A mocked instance of IMainAppView.
        mock_data_inlet1: A mocked instance of DataInlet for Stream1.
        mock_data_inlet2: A mocked instance of DataInlet for Stream2.
    """
    presenter.poll_data()

    mock_data_inlet1.pull_sample.assert_called_once()
    mock_data_inlet2.pull_sample.assert_called_once()

    expected_plot_data1 = {
        "stream_name": "Stream1",
        "data": [0.3, 0.4],
    }
    expected_plot_data2 = {
        "stream_name": "Stream2",
        "data": [1.3, 1.4],
    }

    calls = [
        call.update_plot(expected_plot_data1),
        call.update_plot(expected_plot_data2),
    ]
    mock_view.update_plot.assert_has_calls(calls, any_order=True)


def test_poll_data_no_samples(
    presenter: presenters.main_app_presenter.MainAppPresenter,
    mock_view: MagicMock,
    mock_data_inlet1: MagicMock,
    mock_data_inlet2: MagicMock,
) -> None:
    """Tests the poll_data method when no samples have been pulled yet.

    Args:
        presenter: An instance of MainAppPresenter.
        mock_view: A mocked instance of IMainAppView.
        mock_data_inlet1: A mocked instance of DataInlet for Stream1.
        mock_data_inlet2: A mocked instance of DataInlet for Stream2.
    """
    mock_data_inlet1.ptr = 0
    mock_data_inlet2.ptr = 0

    presenter.poll_data()

    mock_data_inlet1.pull_sample.assert_called_once()
    mock_data_inlet2.pull_sample.assert_called_once()

    mock_view.update_plot.assert_not_called()


def test_poll_data_stream_lost(
    presenter: presenters.main_app_presenter.MainAppPresenter,
    mock_view: MagicMock,
    mock_data_inlet1: MagicMock,
    mock_data_inlet2: MagicMock,
) -> None:
    """Tests the poll_data method when a StreamLostError is raised.

    Args:
        presenter: An instance of MainAppPresenter.
        mock_view: A mocked instance of IMainAppView.
        mock_data_inlet1: A mocked instance of DataInlet for Stream1.
        mock_data_inlet2: A mocked instance of DataInlet for Stream2.
    """
    mock_data_inlet1.pull_sample.side_effect = exceptions.StreamLostError(
        "Stream1 lost."
    )
    mock_data_inlet2.pull_sample.return_value = (mock_data_inlet2.buffers[1], 0.0)
    mock_view.display_error.reset_mock()
    mock_view.update_plot.reset_mock()

    presenter.poll_data()

    mock_data_inlet1.pull_sample.assert_called_once()
    mock_data_inlet2.pull_sample.assert_called_once()
    mock_view.display_error.assert_called_once_with("Stream1 lost.")
    expected_plot_data = {
        "stream_name": "Stream2",
        "data": [1.3, 1.4],
    }
    mock_view.update_plot.assert_called_once_with(expected_plot_data)


def test_poll_data_invalid_channel_count(
    presenter: presenters.main_app_presenter.MainAppPresenter,
    mock_view: MagicMock,
    mock_data_inlet1: MagicMock,
    mock_data_inlet2: MagicMock,
) -> None:
    """Tests the poll_data method when an InvalidChannelCountError is raised.

    Args:
        presenter: An instance of MainAppPresenter.
        mock_view: A mocked instance of IMainAppView.
        mock_data_inlet1: A mocked instance of DataInlet for Stream1.
        mock_data_inlet2: A mocked instance of DataInlet for Stream2.
    """
    mock_data_inlet1.pull_sample.side_effect = exceptions.InvalidChannelCountError(
        "Invalid channel count in Stream1."
    )
    mock_data_inlet2.pull_sample.return_value = (mock_data_inlet2.buffers[1], 0.0)
    mock_view.display_error.reset_mock()
    mock_view.update_plot.reset_mock()

    presenter.poll_data()

    mock_data_inlet1.pull_sample.assert_called_once()
    mock_data_inlet2.pull_sample.assert_called_once()

    mock_view.display_error.assert_called_once_with("Invalid channel count in Stream1.")
    expected_plot_data = {
        "stream_name": "Stream2",
        "data": [1.3, 1.4],
    }
    mock_view.update_plot.assert_called_once_with(expected_plot_data)


def test_poll_data_invalid_channel_format(
    presenter: presenters.main_app_presenter.MainAppPresenter,
    mock_view: MagicMock,
    mock_data_inlet1: MagicMock,
    mock_data_inlet2: MagicMock,
) -> None:
    """Tests the poll_data method when an InvalidChannelFormatError is raised.

    Args:
        presenter: An instance of MainAppPresenter.
        mock_view: A mocked instance of IMainAppView.
        mock_data_inlet1: A mocked instance of DataInlet for Stream1.
        mock_data_inlet2: A mocked instance of DataInlet for Stream2.
    """
    mock_data_inlet1.pull_sample.side_effect = exceptions.InvalidChannelFormatError(
        "Invalid channel format in Stream1."
    )
    mock_data_inlet2.pull_sample.return_value = (mock_data_inlet2.buffers[1], 0.0)
    mock_view.display_error.reset_mock()
    mock_view.update_plot.reset_mock()

    presenter.poll_data()

    mock_data_inlet1.pull_sample.assert_called_once()
    mock_data_inlet2.pull_sample.assert_called_once()
    mock_view.display_error.assert_called_once_with(
        "Invalid channel format in Stream1."
    )
    expected_plot_data = {
        "stream_name": "Stream2",
        "data": [1.3, 1.4],
    }
    mock_view.update_plot.assert_called_once_with(expected_plot_data)


def test_poll_data_unexpected_exception(
    presenter: presenters.main_app_presenter.MainAppPresenter,
    mock_view: MagicMock,
    mock_data_inlet1: MagicMock,
    mock_data_inlet2: MagicMock,
) -> None:
    """Tests the poll_data method when an unexpected exception is raised.

    Args:
        presenter: An instance of MainAppPresenter.
        mock_view: A mocked instance of IMainAppView.
        mock_data_inlet1: A mocked instance of DataInlet for Stream1.
        mock_data_inlet2: A mocked instance of DataInlet for Stream2.
    """
    mock_data_inlet1.pull_sample.side_effect = Exception("Unexpected error in Stream1.")
    mock_data_inlet2.pull_sample.return_value = (mock_data_inlet2.buffers[1], 0.0)
    mock_view.display_error.reset_mock()
    mock_view.update_plot.reset_mock()

    presenter.poll_data()

    mock_data_inlet1.pull_sample.assert_called_once()
    mock_data_inlet2.pull_sample.assert_called_once()
    mock_view.display_error.assert_called_once_with(
        "Unexpected error: Unexpected error in Stream1."
    )
    expected_plot_data = {
        "stream_name": "Stream2",
        "data": [1.3, 1.4],
    }
    mock_view.update_plot.assert_called_once_with(expected_plot_data)


def test_toggle_channel_visibility(
    presenter: presenters.main_app_presenter.MainAppPresenter, mock_view: MagicMock
) -> None:
    """Tests the toggle_channel_visibility method of the Presenter.

    Args:
        presenter: An instance of MainAppPresenter.
        mock_view: A mocked instance of IMainAppView.
    """
    channel_name = "Stream1:Channel1"
    visible = False
    mock_view.toggle_channel_visibility.reset_mock()

    presenter.toggle_channel_visibility(channel_name, visible)

    assert presenter.channel_visibility[channel_name] == visible
    mock_view.toggle_channel_visibility.assert_called_once_with(channel_name, visible)


def test_on_data_updated(
    presenter: presenters.main_app_presenter.MainAppPresenter, mock_view: MagicMock
) -> None:
    """Tests the on_data_updated method to ensure it updates the View correctly.

    Args:
        presenter: An instance of MainAppPresenter.
        mock_view: A mocked instance of IMainAppView.
    """
    stream_name = "Stream1"
    sample = np.array([0.5, 0.6])

    presenter.on_data_updated(stream_name, sample)

    expected_plot_data = {
        "stream_name": stream_name,
        "data": sample.tolist(),
    }
    mock_view.update_plot.assert_called_once_with(expected_plot_data)


def test_on_data_updated_empty_sample(
    presenter: presenters.main_app_presenter.MainAppPresenter, mock_view: MagicMock
) -> None:
    """Tests the on_data_updated method with an empty sample.

    Args:
        presenter: An instance of MainAppPresenter.
        mock_view: A mocked instance of IMainAppView.
    """
    stream_name = "Stream1"
    sample = np.array([])

    presenter.on_data_updated(stream_name, sample)

    expected_plot_data = {"stream_name": stream_name, "data": []}
    mock_view.update_plot.assert_called_once_with(expected_plot_data)
