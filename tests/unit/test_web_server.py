"""Unit tests for web server module."""

import asyncio
import json
from collections.abc import AsyncIterator
from functools import partial
from http.server import SimpleHTTPRequestHandler
from pathlib import Path
from typing import Callable
from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pytest
from pytest_mock import MockFixture

from MoBI_View.core import config
from MoBI_View.presenters.main_app_presenter import MainAppPresenter
from MoBI_View.web import server


@pytest.fixture
def inlet_factory() -> Callable[..., MagicMock]:
    """Factory for creating mock DataInlet objects."""

    def _factory(
        stream_name: str = "TestStream",
        ptr: int = 0,
        channel_count: int = 2,
    ) -> MagicMock:
        inlet = MagicMock()
        inlet.stream_name = stream_name
        inlet.source_id = "test_source"
        inlet.stream_type = "EEG"
        inlet.ptr = ptr
        inlet.sample_rate = 250.0
        inlet.channel_count = channel_count
        inlet.channel_info = {"labels": [f"Ch{i + 1}" for i in range(channel_count)]}
        inlet.buffers = np.zeros((config.Config.BUFFER_SIZE, channel_count))
        return inlet

    return _factory


@pytest.mark.asyncio
async def test_poll_presenter_polls_repeatedly(
    mocker: MockFixture, inlet_factory: Callable[..., MagicMock]
) -> None:
    """Tests poll_presenter_continuously calls poll_data repeatedly."""
    stop_event = asyncio.Event()
    inlet = inlet_factory()
    presenter = MainAppPresenter(data_inlets=[inlet])
    poll_count = 0

    def count_polls() -> list:
        nonlocal poll_count
        poll_count += 1
        if poll_count >= 3:
            stop_event.set()
        return []

    mocker.patch.object(presenter, "poll_data", side_effect=count_polls)
    mocker.patch.object(server.Config, "POLL_INTERVAL", 0.001)

    await server.poll_presenter_continuously(presenter, stop_event)

    assert poll_count >= 3


@pytest.mark.asyncio
async def test_poll_presenter_handles_errors(
    mocker: MockFixture,
    inlet_factory: Callable[..., MagicMock],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Tests poll_presenter_continuously continues after errors."""
    stop_event = asyncio.Event()
    inlet = inlet_factory()
    presenter = MainAppPresenter(data_inlets=[inlet])
    poll_count = 0

    def error_then_succeed() -> list:
        nonlocal poll_count
        poll_count += 1
        if poll_count == 1:
            raise RuntimeError("test error")
        if poll_count >= 3:
            stop_event.set()
        return []

    mocker.patch.object(presenter, "poll_data", side_effect=error_then_succeed)
    mocker.patch.object(server.Config, "POLL_INTERVAL", 0.001)

    await server.poll_presenter_continuously(presenter, stop_event)

    assert poll_count >= 3
    captured = capsys.readouterr()
    assert "Error during polling" in captured.out


@pytest.mark.asyncio
async def test_broadcaster_initializes_correctly(
    inlet_factory: Callable[..., MagicMock],
) -> None:
    """Tests Broadcaster initializes with correct attributes."""
    inlet = inlet_factory()
    presenter = MainAppPresenter(data_inlets=[inlet])

    broadcaster = server.Broadcaster(presenter, interval_ms=50)

    assert broadcaster.presenter == presenter
    assert broadcaster.interval_ms == 50
    assert broadcaster.clients == []


@pytest.mark.asyncio
async def test_broadcaster_start_creates_task(
    inlet_factory: Callable[..., MagicMock],
) -> None:
    """Tests Broadcaster.start creates background task."""
    inlet = inlet_factory()
    presenter = MainAppPresenter(data_inlets=[inlet])
    stop_event = asyncio.Event()
    broadcaster = server.Broadcaster(presenter, interval_ms=1, stop_event=stop_event)

    await broadcaster.start()

    assert broadcaster._task is not None
    broadcaster.stop()
    try:
        await broadcaster._task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_broadcaster_broadcasts_to_clients(
    inlet_factory: Callable[..., MagicMock],
) -> None:
    """Tests Broadcaster sends data to connected clients."""
    inlet = inlet_factory(ptr=5)
    inlet.buffers[4] = np.array([1.5, 2.5])
    presenter = MainAppPresenter(data_inlets=[inlet])
    stop_event = asyncio.Event()
    broadcaster = server.Broadcaster(presenter, interval_ms=1, stop_event=stop_event)
    mock_ws = AsyncMock()
    broadcaster.clients.append(mock_ws)

    await broadcaster.start()
    await asyncio.sleep(0.01)
    broadcaster.stop()

    sent_data = json.loads(mock_ws.send.call_args[0][0])
    assert sent_data["type"] == "sample"
    assert sent_data["streams"][0]["name"] == "TestStream"
    assert sent_data["streams"][0]["data"] == [1.5, 2.5]


@pytest.mark.asyncio
async def test_broadcaster_skips_empty_inlets(
    inlet_factory: Callable[..., MagicMock],
) -> None:
    """Tests Broadcaster skips inlets with no data."""
    inlet_empty = inlet_factory(ptr=0)
    inlet_with_data = inlet_factory(stream_name="Stream2", ptr=3)
    inlet_with_data.buffers[2] = np.array([3.0, 4.0])
    presenter = MainAppPresenter(data_inlets=[inlet_empty, inlet_with_data])
    stop_event = asyncio.Event()
    broadcaster = server.Broadcaster(presenter, interval_ms=1, stop_event=stop_event)
    mock_ws = AsyncMock()
    broadcaster.clients.append(mock_ws)

    await broadcaster.start()
    await asyncio.sleep(0.01)
    broadcaster.stop()

    sent_data = json.loads(mock_ws.send.call_args[0][0])
    assert len(sent_data["streams"]) == 1
    assert sent_data["streams"][0]["name"] == "Stream2"


@pytest.mark.asyncio
async def test_broadcaster_removes_failed_clients(
    inlet_factory: Callable[..., MagicMock],
) -> None:
    """Tests Broadcaster removes clients that fail to receive."""
    inlet = inlet_factory(ptr=1)
    inlet.buffers[0] = np.array([1.0, 2.0])
    presenter = MainAppPresenter(data_inlets=[inlet])
    stop_event = asyncio.Event()
    broadcaster = server.Broadcaster(presenter, interval_ms=1, stop_event=stop_event)
    mock_ws = AsyncMock()
    mock_ws.send = AsyncMock(side_effect=Exception("Connection lost"))
    broadcaster.clients.append(mock_ws)

    await broadcaster.start()
    await asyncio.sleep(0.01)
    broadcaster.stop()

    assert mock_ws not in broadcaster.clients


@pytest.mark.asyncio
async def test_ws_handler_manages_client_lifecycle(
    inlet_factory: Callable[..., MagicMock],
) -> None:
    """Tests ws_handler registers and unregisters clients."""
    inlet = inlet_factory()
    presenter = MainAppPresenter(data_inlets=[inlet])
    broadcaster = server.Broadcaster(presenter)
    mock_ws = AsyncMock()

    async def empty_iter() -> AsyncIterator[str]:
        return
        yield

    mock_ws.__aiter__ = lambda self: empty_iter().__aiter__()

    await server.ws_handler(mock_ws, broadcaster, presenter)

    assert len(broadcaster.clients) == 0


def test_build_static_handler() -> None:
    """Tests build_static_handler returns correct handler."""
    static_dir = Path("/fake/static")

    handler = server.build_static_handler(static_dir)

    assert isinstance(handler, partial)
    assert issubclass(handler.func, SimpleHTTPRequestHandler)  # type: ignore[arg-type]
    assert handler.keywords.get("directory") == str(static_dir)


def test_start_http_server(
    mocker: MockFixture, capsys: pytest.CaptureFixture[str]
) -> None:
    """Tests start_http_static_server starts HTTP server in thread."""
    mock_tcp_server = MagicMock()
    mocker.patch("MoBI_View.web.server.TCPServer", return_value=mock_tcp_server)
    mock_thread = MagicMock()
    mock_thread_class = mocker.patch("MoBI_View.web.server.threading.Thread")
    mock_thread_class.return_value = mock_thread

    server.start_http_static_server("0.0.0.0", 8080)

    assert mock_thread_class.call_args[1]["daemon"] is True
    mock_thread.start.assert_called_once()
    captured = capsys.readouterr()
    assert "Static HTTP server running" in captured.out


@pytest.mark.asyncio
async def test_start_server_creates_websocket_server(
    mocker: MockFixture,
    inlet_factory: Callable[..., MagicMock],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Tests start_server creates and starts WebSocket server."""
    inlet = inlet_factory()
    presenter = MainAppPresenter(data_inlets=[inlet])
    stop_event = asyncio.Event()
    stop_event.set()

    class MockWebSocketServer:
        async def __aenter__(self) -> "MockWebSocketServer":
            return self

        async def __aexit__(self, *args: object) -> None:
            pass

    mock_serve = mocker.patch(
        "MoBI_View.web.server.websocket_serve",
        return_value=MockWebSocketServer(),
    )

    await server.start_server(presenter, stop_event)

    assert mock_serve.called
    captured = capsys.readouterr()
    assert "WebSocket server running" in captured.out


@pytest.mark.asyncio
async def test_run_server_starts_components(
    mocker: MockFixture, inlet_factory: Callable[..., MagicMock]
) -> None:
    """Tests run_server starts HTTP and WebSocket servers."""
    inlet = inlet_factory()
    presenter = MainAppPresenter(data_inlets=[inlet])
    mock_start_http = mocker.patch("MoBI_View.web.server.start_http_static_server")

    async def fake_gather(*tasks: object) -> None:
        for task in tasks:
            if hasattr(task, "close"):
                task.close()  # type: ignore[union-attr]

    mocker.patch("MoBI_View.web.server.asyncio.gather", fake_gather)

    await server.run_server(presenter)

    mock_start_http.assert_called_once()
