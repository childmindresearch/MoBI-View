"""Unit tests for the WebSocket server module."""

import asyncio
import json
import pathlib
import signal
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
from websockets import datastructures

from MoBI_View.presenters import main_app_presenter
from MoBI_View.web import broadcaster, server


@pytest.fixture
def mock_presenter() -> MagicMock:
    """Creates a mock MainAppPresenter."""
    mock = MagicMock(spec=main_app_presenter.MainAppPresenter)
    mock.poll_data.return_value = []
    mock.data_inlets = []
    return mock


@pytest.fixture
def mock_broadcaster(mock_presenter: MagicMock) -> MagicMock:
    """Creates a mock Broadcaster."""
    mock = MagicMock(spec=broadcaster.Broadcaster)
    mock.presenter = mock_presenter
    return mock


@pytest.fixture
def mock_websocket() -> AsyncMock:
    """Creates a mock ServerConnection."""
    return AsyncMock()


def test_ws_handler_registers_and_unregisters_client(
    mock_websocket: AsyncMock,
    mock_broadcaster: MagicMock,
    mock_presenter: MagicMock,
) -> None:
    """Tests ws_handler adds client on connect and removes on disconnect."""
    mock_websocket.__aiter__.return_value = iter([])

    asyncio.run(server.ws_handler(mock_websocket, mock_broadcaster, mock_presenter))

    mock_broadcaster.add_client.assert_called_once_with(mock_websocket)
    mock_broadcaster.remove_client.assert_called_once_with(mock_websocket)


def test_ws_handler_removes_client_on_exception(
    mock_websocket: AsyncMock,
    mock_broadcaster: MagicMock,
    mock_presenter: MagicMock,
) -> None:
    """Tests ws_handler removes client even when iteration raises."""
    mock_websocket.__aiter__.side_effect = RuntimeError("connection lost")

    with pytest.raises(RuntimeError, match="connection lost"):
        asyncio.run(server.ws_handler(mock_websocket, mock_broadcaster, mock_presenter))

    mock_broadcaster.remove_client.assert_called_once_with(mock_websocket)


def test_ws_handler_dispatches_discover_command(
    mock_websocket: AsyncMock,
    mock_broadcaster: MagicMock,
    mock_presenter: MagicMock,
) -> None:
    """Tests ws_handler forwards a discover command to _handle_discover."""
    message = json.dumps({"command": "discover"})
    mock_websocket.__aiter__.return_value = iter([message])

    with patch.object(server, "_handle_discover", new_callable=AsyncMock) as mock_hd:
        asyncio.run(server.ws_handler(mock_websocket, mock_broadcaster, mock_presenter))

        mock_hd.assert_awaited_once_with(mock_websocket, mock_presenter)


def test_handle_message_ignores_invalid_json(
    mock_websocket: AsyncMock,
    mock_presenter: MagicMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Tests _handle_message logs warning for non-JSON payload."""
    asyncio.run(server._handle_message("not json", mock_websocket, mock_presenter))

    assert "invalid JSON" in caplog.text


def test_handle_message_rejects_non_string_input(
    mock_websocket: AsyncMock,
    mock_presenter: MagicMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Tests _handle_message logs warning when input is not str or bytes."""
    asyncio.run(
        server._handle_message(None, mock_websocket, mock_presenter)  # type: ignore[arg-type]
    )

    assert "invalid JSON" in caplog.text


def test_handle_message_rejects_invalid_bytes(
    mock_websocket: AsyncMock,
    mock_presenter: MagicMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Tests _handle_message logs warning for bytes with invalid encoding."""
    asyncio.run(server._handle_message(b"\xff\xfe", mock_websocket, mock_presenter))

    assert "invalid JSON" in caplog.text


def test_handle_message_rejects_deeply_nested_json(
    mock_websocket: AsyncMock,
    mock_presenter: MagicMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Tests _handle_message logs warning for deeply nested JSON."""
    deeply_nested = "[" * 10000 + "]" * 10000

    asyncio.run(server._handle_message(deeply_nested, mock_websocket, mock_presenter))

    assert "invalid JSON" in caplog.text


def test_handle_message_rejects_non_dict_json(
    mock_websocket: AsyncMock,
    mock_presenter: MagicMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Tests _handle_message logs warning when JSON is not an object."""
    asyncio.run(
        server._handle_message('"just a string"', mock_websocket, mock_presenter)
    )

    assert "Expected JSON object" in caplog.text


def test_handle_message_logs_unknown_command(
    mock_websocket: AsyncMock,
    mock_presenter: MagicMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Tests _handle_message logs warning for unrecognised command."""
    msg = json.dumps({"command": "foobar"})

    asyncio.run(server._handle_message(msg, mock_websocket, mock_presenter))

    assert "Unknown command: foobar" in caplog.text


def test_handle_message_routes_discover_command(
    mock_websocket: AsyncMock,
    mock_presenter: MagicMock,
) -> None:
    """Tests _handle_message calls _handle_discover for discover command."""
    msg = json.dumps({"command": "discover"})

    with patch.object(server, "_handle_discover", new_callable=AsyncMock) as mock_hd:
        asyncio.run(server._handle_message(msg, mock_websocket, mock_presenter))

        mock_hd.assert_awaited_once_with(mock_websocket, mock_presenter)


def test_handle_discover_calls_discovery_and_sends_result(
    mock_websocket: AsyncMock,
    mock_presenter: MagicMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Tests _handle_discover discovers new streams and sends them to client."""
    fake_inlet = MagicMock()
    fake_inlet.stream_name = "EEG"

    with (
        patch.object(
            server.discovery,
            "discover_and_create_inlets",
            return_value=[fake_inlet],
        ),
        caplog.at_level("INFO"),
    ):
        asyncio.run(server._handle_discover(mock_websocket, mock_presenter))

    mock_websocket.send.assert_awaited_once()
    sent = json.loads(mock_websocket.send.call_args[0][0])
    assert sent["type"] == "discover_result"
    assert sent["streams"] == ["EEG"]
    assert fake_inlet in mock_presenter.data_inlets
    assert "found 1 new stream(s)" in caplog.text


def test_handle_discover_with_no_new_streams(
    mock_websocket: AsyncMock,
    mock_presenter: MagicMock,
) -> None:
    """Tests _handle_discover sends empty list when no new streams found."""
    with patch.object(
        server.discovery,
        "discover_and_create_inlets",
        return_value=[],
    ):
        asyncio.run(server._handle_discover(mock_websocket, mock_presenter))

    sent = json.loads(mock_websocket.send.call_args[0][0])
    assert sent["streams"] == []


@pytest.fixture
def static_dir(tmp_path: pathlib.Path) -> pathlib.Path:
    """Creates a temporary static directory mimicking SvelteKit build output."""
    (tmp_path / "index.html").write_text("<html></html>")
    (tmp_path / "style.css").write_text("body {}")
    app_dir = tmp_path / "_app" / "immutable"
    app_dir.mkdir(parents=True)
    (app_dir / "entry.js").write_text("console.log('ok')")
    return tmp_path


def _make_request(path: str, upgrade: str = "") -> MagicMock:
    """Builds a minimal Request-like object with path and headers."""
    header_list = []
    if upgrade:
        header_list.append(("Upgrade", upgrade))
    request = MagicMock()
    request.path = path
    request.headers = datastructures.Headers(header_list)
    return request


def test_process_request_passes_websocket_upgrades() -> None:
    """Tests process_request returns None for WebSocket upgrades."""
    request = _make_request("/", upgrade="websocket")
    connection = MagicMock()

    result = asyncio.run(server.process_request(connection, request))

    assert result is None


def test_process_request_serves_static_file() -> None:
    """Tests process_request delegates to _serve_static_file for HTTP requests."""
    request = _make_request("/style.css")
    connection = MagicMock()
    fake_response = MagicMock()

    with patch.object(
        server, "_serve_static_file", return_value=fake_response
    ) as mock_serve:
        result = asyncio.run(server.process_request(connection, request))

    mock_serve.assert_called_once_with("/style.css")
    assert result is fake_response


@pytest.mark.parametrize("path", ["/", ""])
def test_serve_static_file_returns_index_for_root_paths(
    path: str,
    static_dir: pathlib.Path,
) -> None:
    """Tests root and empty paths both resolve to index.html."""
    with patch.object(server, "STATIC_DIR", static_dir):
        result = server._serve_static_file(path)

    assert result.status_code == 200
    assert b"<html></html>" in result.body


def test_serve_static_file_returns_nested_file(
    static_dir: pathlib.Path,
) -> None:
    """Tests subdirectory files are served correctly."""
    with patch.object(server, "STATIC_DIR", static_dir):
        result = server._serve_static_file("/_app/immutable/entry.js")

    assert result.status_code == 200
    assert b"console.log" in result.body


def test_serve_static_file_returns_correct_content_type(
    static_dir: pathlib.Path,
) -> None:
    """Tests Content-Type header matches the file extension."""
    with patch.object(server, "STATIC_DIR", static_dir):
        result = server._serve_static_file("/style.css")

    assert result.status_code == 200
    assert "css" in result.headers.get("Content-Type", "")


def test_serve_static_file_returns_404_for_missing_file(
    static_dir: pathlib.Path,
) -> None:
    """Tests missing files return a 404 response."""
    with patch.object(server, "STATIC_DIR", static_dir):
        result = server._serve_static_file("/nope.txt")

    assert result.status_code == 404


@pytest.mark.parametrize(
    "malicious_path",
    [
        "/../../../etc/passwd",
        "/%2e%2e/%2e%2e/etc/passwd",
        "/..%2F..%2Fetc/passwd",
    ],
)
def test_serve_static_file_blocks_path_traversal(
    malicious_path: str, static_dir: pathlib.Path
) -> None:
    """Tests path traversal attempts return a 403 response."""
    with patch.object(server, "STATIC_DIR", static_dir):
        result = server._serve_static_file(malicious_path)

    assert result.status_code == 403


@pytest.mark.parametrize(
    "resolved,expected",
    [
        ("inside", True),
        ("outside", False),
    ],
)
def test_is_within_static_dir(
    resolved: str,
    expected: bool,
    tmp_path: pathlib.Path,
) -> None:
    """Tests path containment check against the static directory."""
    static = tmp_path / "static"
    static.mkdir()

    if resolved == "inside":
        target = static / "file.html"
    else:
        target = tmp_path / "file.html"

    with patch.object(server, "STATIC_DIR", static):
        assert server._is_within_static_dir(target) is expected


def test_run_server_calls_asyncio_run(mock_presenter: MagicMock) -> None:
    """Tests run_server delegates to _run_server_async via asyncio.run."""
    with patch.object(
        server, "_run_server_async", new_callable=AsyncMock
    ) as mock_async:
        server.run_server(mock_presenter, host="0.0.0.0", port=9000)

    mock_async.assert_awaited_once_with(mock_presenter, "0.0.0.0", 9000)


async def test_run_server_async_starts_and_stops_broadcaster(
    mock_presenter: MagicMock,
) -> None:
    """Tests _run_server_async creates, starts, and stops the broadcaster."""
    mock_bc = MagicMock(spec=broadcaster.Broadcaster)
    mock_serve = AsyncMock()
    mock_serve.__aenter__ = AsyncMock()
    mock_serve.__aexit__ = AsyncMock(return_value=False)

    with (
        patch.object(
            server.broadcaster, "Broadcaster", return_value=mock_bc
        ) as mock_bc_cls,
        patch.object(server.server, "serve", return_value=mock_serve) as mock_serve_fn,
        patch.object(server, "_register_shutdown_signals") as mock_signals,
    ):
        mock_signals.side_effect = lambda event: event.set()

        await server._run_server_async(mock_presenter, "localhost", 8765)

    mock_bc_cls.assert_called_once_with(mock_presenter)
    mock_bc.start.assert_called_once()
    mock_bc.stop.assert_called_once()

    _, serve_kwargs = mock_serve_fn.call_args
    assert serve_kwargs["process_request"] is server.process_request


async def test_run_server_async_stops_broadcaster_on_error(
    mock_presenter: MagicMock,
) -> None:
    """Tests broadcaster is stopped even when the server raises."""
    mock_bc = MagicMock(spec=broadcaster.Broadcaster)
    mock_serve = AsyncMock()
    mock_serve.__aenter__ = AsyncMock(side_effect=OSError("address in use"))
    mock_serve.__aexit__ = AsyncMock(return_value=False)

    with (
        patch.object(server.broadcaster, "Broadcaster", return_value=mock_bc),
        patch.object(server.server, "serve", return_value=mock_serve),
        patch.object(server, "_register_shutdown_signals"),
    ):
        with pytest.raises(OSError, match="address in use"):
            await server._run_server_async(mock_presenter, "localhost", 8765)

    mock_bc.stop.assert_called_once()


async def test_register_shutdown_signals_registers_both_signals() -> None:
    """Tests both SIGINT and SIGTERM are registered on the event loop."""
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    with patch.object(loop, "add_signal_handler") as mock_add:
        server._register_shutdown_signals(stop_event)

    mock_add.assert_has_calls(
        [call(signal.SIGINT, stop_event.set), call(signal.SIGTERM, stop_event.set)],
        any_order=False,
    )
