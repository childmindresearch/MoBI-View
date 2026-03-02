"""WebSocket server for MoBI-View real-time data streaming.

This module provides the ws_handler coroutine that manages WebSocket
client connections and handles incoming discover messages.
"""

import json
import logging

from websockets.asyncio import server

from MoBI_View.core import discovery
from MoBI_View.presenters import main_app_presenter
from MoBI_View.web import broadcaster

logger = logging.getLogger("MoBI-View.web.server")


async def ws_handler(
    websocket: server.ServerConnection,
    active_broadcaster: broadcaster.Broadcaster,
    presenter: main_app_presenter.MainAppPresenter,
) -> None:
    """Handle a WebSocket client connection.

    Registers the client with the broadcaster, listens for incoming
    messages, and removes the client on disconnect.

    Args:
        websocket: The WebSocket connection.
        active_broadcaster: The Broadcaster instance managing clients.
        presenter: The MainAppPresenter providing data and inlets.
    """
    active_broadcaster.add_client(websocket)
    try:
        async for raw_message in websocket:
            await _handle_message(raw_message, websocket, presenter)
    finally:
        active_broadcaster.remove_client(websocket)


async def _handle_message(
    raw_message: str | bytes,
    websocket: server.ServerConnection,
    presenter: main_app_presenter.MainAppPresenter,
) -> None:
    """Parse and dispatch a single client message.

    Currently supports only the `discover` command. As the number of
    supported commands grows, this function should be refactored to use a
    dispatch table (e.g. `handlers = {"discover": _handle_discover}`)
    instead of explicit `if/else` branching.

    Args:
        raw_message: The raw message received from the WebSocket.
        websocket: The WebSocket connection for sending responses.
        presenter: The MainAppPresenter for stream management.
    """
    try:
        data = json.loads(raw_message)
    except (json.JSONDecodeError, TypeError, UnicodeDecodeError, RecursionError):
        logger.warning("Received invalid JSON")
        return

    if not isinstance(data, dict):
        logger.warning("Expected JSON object, got %s", type(data).__name__)
        return

    command = data.get("command")
    if command == "discover":
        await _handle_discover(websocket, presenter)
    else:
        logger.warning("Unknown command: %s", command)


async def _handle_discover(
    websocket: server.ServerConnection,
    presenter: main_app_presenter.MainAppPresenter,
) -> None:
    """Run stream discovery and send results to the requesting client.

    Args:
        websocket: The WebSocket connection to send the result to.
        presenter: The MainAppPresenter managing data inlets.
    """
    new_inlets = discovery.discover_and_create_inlets(
        existing_inlets=presenter.data_inlets,
    )
    presenter.data_inlets.extend(new_inlets)
    stream_names = [inlet.stream_name for inlet in new_inlets]
    response = json.dumps(
        {
            "type": "discover_result",
            "streams": stream_names,
        }
    )
    await websocket.send(response)
    logger.info("Discover: found %d new stream(s)", len(new_inlets))
