"""Unit tests for the WebSocket server module."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

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


def test_handle_discover_passes_existing_inlets(
    mock_websocket: AsyncMock,
    mock_presenter: MagicMock,
) -> None:
    """Tests _handle_discover passes presenter.data_inlets to discovery."""
    existing = [MagicMock()]
    mock_presenter.data_inlets = existing

    with patch.object(
        server.discovery,
        "discover_and_create_inlets",
        return_value=[],
    ) as mock_discover:
        asyncio.run(server._handle_discover(mock_websocket, mock_presenter))

    mock_discover.assert_called_once_with(existing_inlets=existing)
