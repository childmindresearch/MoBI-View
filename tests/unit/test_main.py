"""Unit tests for main application entry point."""

from typing import Any, Callable
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockFixture

from MoBI_View import main as main_module


class FakeTimer:
    """Test double for threading.Timer."""

    def __init__(self, delay: float, func: Callable[[], None]) -> None:
        """Initialize fake timer with delay and function."""
        self.delay = delay
        self.func = func
        self.daemon = False

    def start(self) -> None:
        """Start timer by immediately calling function."""
        self.func()


def test_schedule_browser_launch_converts_wildcard_to_localhost(
    mocker: MockFixture,
) -> None:
    """Tests schedule_browser_launch converts 0.0.0.0 to localhost."""
    browser_calls: dict[str, Any] = {}

    def capture_open(url: str, new: int, autoraise: bool) -> None:
        browser_calls["url"] = url

    mocker.patch.object(main_module.threading, "Timer", FakeTimer)
    mocker.patch.object(main_module.webbrowser, "open", capture_open)
    mocker.patch.object(main_module.Config, "HTTP_HOST", "0.0.0.0")
    mocker.patch.object(main_module.Config, "HTTP_PORT", 8080)

    main_module.schedule_browser_launch()

    assert browser_calls["url"] == "http://localhost:8080"


def test_main_discovers_and_starts_server(
    mocker: MockFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Tests main discovers streams and starts server."""
    mock_inlet = MagicMock()
    mock_inlet.stream_name = "TestStream"
    mocker.patch(
        "MoBI_View.main.discover_and_create_inlets",
        return_value=([mock_inlet], 1),
    )
    mock_presenter_class = mocker.patch("MoBI_View.main.MainAppPresenter")
    mocker.patch("MoBI_View.main.schedule_browser_launch")
    mock_asyncio_run = mocker.patch("MoBI_View.main.asyncio.run")
    mocker.patch("MoBI_View.main.run_server")

    main_module.main()

    mock_presenter_class.assert_called_once_with(data_inlets=[mock_inlet])
    mock_asyncio_run.assert_called_once()
    captured = capsys.readouterr()
    assert "Found 1 stream(s)" in captured.out


def test_main_handles_no_streams(
    mocker: MockFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Tests main handles case when no streams are found."""
    mocker.patch(
        "MoBI_View.main.discover_and_create_inlets",
        return_value=([], 0),
    )
    mock_presenter_class = mocker.patch("MoBI_View.main.MainAppPresenter")
    mocker.patch("MoBI_View.main.schedule_browser_launch")
    mock_run_server = mocker.patch("MoBI_View.main.run_server")

    def mock_asyncio_run(coro: object) -> None:
        pass

    mocker.patch("MoBI_View.main.asyncio.run", side_effect=mock_asyncio_run)

    main_module.main()

    mock_presenter_class.assert_called_once_with(data_inlets=[])
    mock_run_server.assert_called_once()
    captured = capsys.readouterr()
    assert "No LSL streams found" in captured.out
