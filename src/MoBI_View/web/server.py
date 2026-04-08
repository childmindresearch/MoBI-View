"""WebSocket server for MoBI-View real-time data streaming.

This module provides WebSocket connection handling and static file serving
via the websockets process_request hook.
"""

import json
import logging
import mimetypes
import pathlib
from urllib import parse

from websockets import datastructures, http11
from websockets.asyncio import server

from MoBI_View.core import discovery
from MoBI_View.presenters import main_app_presenter
from MoBI_View.web import broadcaster

logger = logging.getLogger("MoBI-View.web.server")

STATIC_DIR = pathlib.Path(__file__).resolve().parent / "static"


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


async def process_request(
    connection: server.ServerConnection,
    request: http11.Request,
) -> http11.Response | None:
    """Serve static files or pass through to WebSocket upgrade.

    Intercepts HTTP requests before the WebSocket handshake. Requests with
    an ``Upgrade: websocket`` header proceed to ws_handler. All other
    requests are resolved against the static directory.

    Args:
        connection: The server connection being handled.
        request: The incoming HTTP request.

    Returns:
        A Response for static file requests, or None for WebSocket upgrades.
    """
    if _is_websocket_upgrade(request):
        return None
    return _serve_static_file(request.path)


def _is_websocket_upgrade(request: http11.Request) -> bool:
    """Check whether the request is a WebSocket upgrade."""
    return request.headers.get("Upgrade", "").lower() == "websocket"


def _serve_static_file(request_path: str) -> http11.Response:
    """Resolve a URL path to a file in the static directory.

    Decodes percent-encoded characters, normalises the path, and verifies
    the result stays within STATIC_DIR before reading.

    Two safety checks are applied in order:
        1. Path containment - if the resolved path escapes STATIC_DIR
           (e.g. via ``../`` traversal), returns HTTP 403 Forbidden.
        2. File existence - if the path is inside STATIC_DIR but does
           not point to an existing file, returns HTTP 404 Not Found.

    Args:
        request_path: The URL path from the HTTP request.

    Returns:
        An HTTP 200 response with file contents on success,
        HTTP 403 Forbidden if the path escapes the static directory,
        or HTTP 404 Not Found if the file does not exist.
    """
    decoded = parse.unquote(request_path)
    if decoded in ("", "/"):
        decoded = "/index.html"
    relative = decoded.lstrip("/")
    resolved = (STATIC_DIR / relative).resolve()
    if not _is_within_static_dir(resolved):
        return _error_response(403, "Forbidden")
    if not resolved.is_file():
        return _error_response(404, "Not Found")
    content_type = mimetypes.guess_type(str(resolved))[0] or "application/octet-stream"
    body = resolved.read_bytes()
    headers = datastructures.Headers([("Content-Type", content_type)])
    return http11.Response(200, "OK", headers, body)


def _is_within_static_dir(resolved_path: pathlib.Path) -> bool:
    """Verify the resolved path is within the static directory."""
    try:
        resolved_path.relative_to(STATIC_DIR)
        return True
    except ValueError:
        return False


def _error_response(status_code: int, reason: str) -> http11.Response:
    """Build a plain-text HTTP error response."""
    headers = datastructures.Headers([("Content-Type", "text/plain")])
    return http11.Response(status_code, reason, headers, reason.encode())
