"""Unit tests for the MainAppPresenter class in the MoBI_View package."""

from unittest.mock import MagicMock

import numpy as np
import pytest
from pytest_mock import MockFixture

from MoBI_View.core import data_inlet, exceptions
from MoBI_View.presenters import main_app_presenter
from MoBI_View.views import interfaces


@pytest.fixture
def mock_view(mocker: MockFixture) -> MagicMock:
    """Creates a mock instance of IMainAppView."""
    view_mock = mocker.MagicMock(spec=interfaces.IMainAppView)
    return view_mock


@pytest.fixture
def mock_data_inlet(mocker: MockFixture) -> MagicMock:
    """Creates the first mock instance of DataInlet."""
    inlet_mock = mocker.MagicMock(spec=data_inlet.DataInlet)
    inlet_mock.stream_name = "Stream1"
    inlet_mock.channel_info = {"labels": ["Channel1", "Channel2"]}
    inlet_mock.buffers = np.array([[0.1, 0.2], [0.3, 0.4]])
    inlet_mock.ptr = 2
    return inlet_mock


@pytest.fixture
def presenter(
    mocker: MockFixture,
    mock_view: MagicMock,
    mock_data_inlet: MagicMock,
) -> main_app_presenter.MainAppPresenter:
    """Creates an instance of MainAppPresenter with mocked dependencies.

    Args:
        mocker: A fixture for mocking.
        mock_view: A mocked IMainAppView.
        mock_data_inlet: A mocked DataInlet.
    """
    mock_timer_instance = mocker.MagicMock()
    mocker.patch("PyQt6.QtCore.QTimer", return_value=mock_timer_instance)
    presenter_instance = main_app_presenter.MainAppPresenter(
        view=mock_view, data_inlets=[mock_data_inlet]
    )
    return presenter_instance


def test_presenter_initialization(
    presenter: MagicMock,
    mock_view: MagicMock,
) -> None:
    """Tests the initialization of the MainAppPresenter class.

    Args:
        presenter: An instance of MainAppPresenter.
        mock_view: A mocked instance of IMainAppView.
    """
    expected_visibility_items = [
        ("Stream1:Channel1", True),
        ("Stream1:Channel2", True),
    ]
    args1, _ = mock_view.set_plot_channel_visibility.call_args_list[0]
    args2, _ = mock_view.set_plot_channel_visibility.call_args_list[1]

    assert presenter.channel_visibility == dict(expected_visibility_items)
    assert mock_view.set_plot_channel_visibility.call_count == 2
    assert args1 == expected_visibility_items[0]
    assert args2 == expected_visibility_items[1]


def test_poll_data_success(
    presenter: main_app_presenter.MainAppPresenter,
    mock_view: MagicMock,
    mock_data_inlet: MagicMock,
) -> None:
    """Tests poll_data when data is successfully pulled from DataInlets.

    Args:
        presenter: An instance of MainAppPresenter.
        mock_view: A mocked instance of IMainAppView.
        mock_data_inlet: A mocked instance of DataInlet.
    """
    expected_plot_data = {
        "stream_name": "Stream1",
        "data": [0.3, 0.4],
        "channel_labels": ["Channel1", "Channel2"],
    }

    presenter.poll_data()

    mock_data_inlet.pull_sample.assert_called_once()
    mock_view.update_plot.assert_called_once_with(expected_plot_data)


def test_poll_data_no_samples(
    presenter: main_app_presenter.MainAppPresenter,
    mock_view: MagicMock,
    mock_data_inlet: MagicMock,
) -> None:
    """Tests poll_data when no samples have been pulled yet.

    Args:
        presenter: An instance of MainAppPresenter.
        mock_view: A mocked instance of IMainAppView.
        mock_data_inlet: A mocked instance of DataInlet.
    """
    mock_data_inlet.ptr = 0

    presenter.poll_data()

    mock_data_inlet.pull_sample.assert_called_once()
    mock_view.update_plot.assert_not_called()


def test_poll_data_stream_lost(
    presenter: main_app_presenter.MainAppPresenter,
    mock_view: MagicMock,
    mock_data_inlet: MagicMock,
) -> None:
    """Tests poll_data when a StreamLostError is raised.

    Args:
        presenter: An instance of MainAppPresenter.
        mock_view: A mocked instance of IMainAppView.
        mock_data_inlet: A mocked instance of DataInlet.
    """
    mock_data_inlet.pull_sample.side_effect = exceptions.StreamLostError(
        "Stream1 lost."
    )

    presenter.poll_data()

    mock_data_inlet.pull_sample.assert_called_once()
    mock_view.display_error.assert_called_once_with("Stream1 lost.")


def test_poll_data_invalid_channel_count(
    presenter: main_app_presenter.MainAppPresenter,
    mock_view: MagicMock,
    mock_data_inlet: MagicMock,
) -> None:
    """Tests poll_data when an InvalidChannelCountError is raised.

    Args:
        presenter: An instance of MainAppPresenter.
        mock_view: A mocked instance of IMainAppView.
        mock_data_inlet: A mocked instance of DataInlet.
    """
    mock_data_inlet.pull_sample.side_effect = exceptions.InvalidChannelCountError(
        "Invalid channel count in Stream1."
    )

    presenter.poll_data()

    mock_data_inlet.pull_sample.assert_called_once()
    mock_view.display_error.assert_called_once_with("Invalid channel count in Stream1.")


def test_poll_data_invalid_channel_format(
    presenter: main_app_presenter.MainAppPresenter,
    mock_view: MagicMock,
    mock_data_inlet: MagicMock,
) -> None:
    """Tests poll_data when an InvalidChannelFormatError is raised.

    Args:
        presenter: An instance of MainAppPresenter.
        mock_view: A mocked instance of IMainAppView.
        mock_data_inlet: A mocked instance of DataInlet.
    """
    mock_data_inlet.pull_sample.side_effect = exceptions.InvalidChannelFormatError(
        "Invalid channel format in Stream1."
    )

    presenter.poll_data()

    mock_data_inlet.pull_sample.assert_called_once()
    mock_view.display_error.assert_called_once_with(
        "Invalid channel format in Stream1."
    )


def test_poll_data_unexpected_exception(
    presenter: main_app_presenter.MainAppPresenter,
    mock_view: MagicMock,
    mock_data_inlet: MagicMock,
) -> None:
    """Tests poll_data when an unexpected exception is raised.

    Args:
        presenter: An instance of MainAppPresenter.
        mock_view: A mocked instance of IMainAppView.
        mock_data_inlet: A mocked instance of DataInlet.
    """
    mock_data_inlet.pull_sample.side_effect = Exception("Unexpected error in Stream1.")

    presenter.poll_data()

    mock_data_inlet.pull_sample.assert_called_once()
    mock_view.display_error.assert_called_once_with(
        "Unexpected error: Unexpected error in Stream1."
    )


def test_update_channel_visibility(
    presenter: main_app_presenter.MainAppPresenter, mock_view: MagicMock
) -> None:
    """Tests update_channel_visibility of the Presenter.

    Args:
        presenter: An instance of MainAppPresenter.
        mock_view: A mocked instance of IMainAppView.
    """
    channel_name = "Stream1:Channel1"
    visible = False
    mock_view.set_plot_channel_visibility.reset_mock()

    presenter.update_channel_visibility(channel_name, visible)

    assert presenter.channel_visibility[channel_name] == visible
    mock_view.set_plot_channel_visibility.assert_called_once_with(channel_name, visible)


def test_on_data_updated(
    presenter: main_app_presenter.MainAppPresenter, mock_view: MagicMock
) -> None:
    """Tests on_data_updated to ensure it updates the View correctly.

    Args:
        presenter: An instance of MainAppPresenter.
        mock_view: A mocked instance of IMainAppView.
    """
    stream_name = "Stream1"
    sample = np.array([0.5, 0.6])
    channel_labels = ["Channel1", "Channel2"]
    expected_plot_data = {
        "stream_name": stream_name,
        "data": sample.tolist(),
        "channel_labels": channel_labels,
    }

    presenter.on_data_updated(stream_name, sample, channel_labels)

    mock_view.update_plot.assert_called_once_with(expected_plot_data)


def test_on_data_updated_empty_sample(
    presenter: main_app_presenter.MainAppPresenter, mock_view: MagicMock
) -> None:
    """Tests on_data_updated with an empty sample.

    Args:
        presenter: An instance of MainAppPresenter.
        mock_view: A mocked instance of IMainAppView.
    """
    stream_name = "Stream1"
    sample = np.array([])
    channel_labels: list[str] = []
    expected_plot_data = {
        "stream_name": stream_name,
        "data": [],
        "channel_labels": channel_labels,
    }

    presenter.on_data_updated(stream_name, sample, channel_labels)

    mock_view.update_plot.assert_called_once_with(expected_plot_data)
