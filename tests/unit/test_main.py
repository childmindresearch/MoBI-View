"""Unit tests for the main entry point of the MoBI_View application.

This module tests the behavior of main() when processing valid streams and when
DataInlet initialization fails for a stream.
"""

from unittest.mock import MagicMock, patch

import pytest

from MoBI_View.main import main


class DummyStream:
    """A dummy object with a name() method used to simulate pylsl stream info."""

    def __init__(self, name: str) -> None:
        """Initialize a DummyStream with the given name."""
        self._name = name

    def name(self) -> str:
        """Return the name of the dummy stream."""
        return self._name


@pytest.fixture
def fake_app() -> MagicMock:
    """Fixture for a fake QApplication instance with an exec method."""
    fake_app = MagicMock(name="fake_app")
    fake_app.exec.return_value = 0
    return fake_app


def test_main_success(capsys: pytest.CaptureFixture, fake_app: MagicMock) -> None:
    """Tests main() when stream resolution and DataInlet creation are successful.

    It asserts that the stream is processed, the view and presenter are created with the
    correct parameters, and the application event loop is started.
    """
    dummy_info = DummyStream("DummySuccess")

    fake_inlet = MagicMock(name="fake_inlet")
    fake_inlet.stream_name = "TestStream"
    fake_inlet.stream_type = "EEG"

    fake_view_instance = MagicMock(name="fake_view_instance")

    with (
        patch(
            "MoBI_View.main.resolve_streams", return_value=[dummy_info]
        ) as mock_resolve_streams,
        patch("MoBI_View.main.DataInlet", return_value=fake_inlet) as mock_DataInlet,
        patch(
            "MoBI_View.main.MainAppView", return_value=fake_view_instance
        ) as mock_MainAppView,
        patch("MoBI_View.main.MainAppPresenter") as mock_MainAppPresenter,
        patch(
            "MoBI_View.main.QApplication", return_value=fake_app
        ) as _mock_QApplication,
        patch("MoBI_View.main.sys.exit") as mock_sys_exit,
    ):
        main()
        captured = capsys.readouterr().out

        mock_resolve_streams.assert_called_once()
        mock_DataInlet.assert_called_once_with(dummy_info)
        mock_MainAppView.assert_called_once_with(stream_info={"TestStream": "EEG"})
        mock_MainAppPresenter.assert_called_once_with(
            view=fake_view_instance, data_inlets=[fake_inlet]
        )
        fake_view_instance.show.assert_called_once()
        fake_app.exec.assert_called_once()
        mock_sys_exit.assert_called_once_with(0)
        assert "Resolving LSL streams..." in captured
        assert "Discovered stream: Name=TestStream, Type=EEG" in captured
        assert "Starting application event loop..." in captured


def test_main_with_exception(
    capsys: pytest.CaptureFixture, fake_app: MagicMock
) -> None:
    """Tests main() when DataInlet construction raises exception for one of the streams.

    Two dummy streams are provided:
      - The first succeeds (simulated by returning a valid inlet),
      - The second triggers an exception within DataInlet().

    The test asserts that the failing stream is skipped (and an error message printed),
    that MainAppView and MainAppPresenter are created only for the successful stream,
    and that the application event loop is started as normal.
    """
    dummy_info_success = DummyStream("DummySuccess")
    dummy_info_failure = DummyStream("DummyFailure")

    fake_inlet = MagicMock(name="fake_inlet")
    fake_inlet.stream_name = "SuccessStream"
    fake_inlet.stream_type = "EEG"

    fake_view_instance = MagicMock(name="fake_view_instance")

    def data_inlet_side_effect(info: DummyStream) -> MagicMock:
        if info.name() == "DummyFailure":
            raise Exception("Dummy error")
        else:
            return fake_inlet

    with (
        patch(
            "MoBI_View.main.resolve_streams",
            return_value=[dummy_info_success, dummy_info_failure],
        ) as mock_resolve_streams,
        patch(
            "MoBI_View.main.DataInlet", side_effect=data_inlet_side_effect
        ) as mock_DataInlet,
        patch(
            "MoBI_View.main.MainAppView", return_value=fake_view_instance
        ) as mock_MainAppView,
        patch("MoBI_View.main.MainAppPresenter") as mock_MainAppPresenter,
        patch(
            "MoBI_View.main.QApplication", return_value=fake_app
        ) as _mock_QApplication,
        patch("MoBI_View.main.sys.exit") as mock_sys_exit,
    ):
        main()
        captured = capsys.readouterr().out

        mock_resolve_streams.assert_called_once()
        assert mock_DataInlet.call_count == 2
        mock_MainAppView.assert_called_once_with(stream_info={"SuccessStream": "EEG"})
        mock_MainAppPresenter.assert_called_once_with(
            view=fake_view_instance, data_inlets=[fake_inlet]
        )
        fake_view_instance.show.assert_called_once()
        fake_app.exec.assert_called_once()
        mock_sys_exit.assert_called_once_with(0)
        assert "Skipping stream DummyFailure due to error: Dummy error" in captured
        assert "Resolving LSL streams..." in captured
        assert "Starting application event loop..." in captured
