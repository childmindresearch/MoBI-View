"""WebSocket server that broadcasts LSL data to browser clients.

Serves static files via HTTP and broadcasts real-time data to WebSocket clients.
Handles WebSocket connections and "discover streams" requests from the browser.
"""

from __future__ import annotations

import asyncio
import json
import threading
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler
from pathlib import Path
from socketserver import TCPServer
from typing import Any, Callable

import websockets

from MoBI_View.core.config import Config
from MoBI_View.presenters.main_app_presenter import MainAppPresenter

try:
    import websockets.asyncio.server as websockets_server
except ImportError:  # pragma: no cover - legacy fallback for websockets<14
    websockets_server = getattr(websockets, "server")  # type: ignore[attr-defined]

websocket_serve: Any = getattr(websockets_server, "serve")  # type: ignore[attr-defined]

WebSocketConnection = Any


class Broadcaster:
    """Broadcasts data from presenter to WebSocket clients.

    Maintains list of connected clients and periodically sends formatted
    JSON frames with stream data from presenter.data_inlets.
    """

    def __init__(
        self,
        presenter: MainAppPresenter,
        interval_ms: int | None = None,
        stop_event: asyncio.Event | None = None,
    ) -> None:
        """Initialize broadcaster with presenter and broadcast interval.

        Args:
            presenter: MainAppPresenter instance with data_inlets to read from.
            interval_ms: Broadcast interval in milliseconds (default from Config).
            stop_event: Optional asyncio.Event to signal shutdown (for testing).
        """
        self.presenter = presenter
        self.interval_ms = interval_ms or Config.TIMER_INTERVAL
        self.clients: list[WebSocketConnection] = []
        self._task: asyncio.Task | None = None
        self._stop_event = stop_event

    async def start(self) -> None:
        """Launch the background broadcasting loop as an asyncio task."""
        if self._stop_event is None:
            self._stop_event = asyncio.Event()
        self._task = asyncio.create_task(self._run())

    def stop(self) -> None:
        """Stops the broadcaster by canceling its task."""
        if self._stop_event is not None:
            self._stop_event.set()
        if self._task is not None:
            self._task.cancel()

    async def _run(self) -> None:
        """Broadcasts data from presenter to clients at fixed intervals."""
        while True:
            started_at = time.time()
            if self.clients:
                streams_out: list[dict[str, Any]] = []

                for inlet in self.presenter.data_inlets:
                    if inlet.ptr == 0:
                        continue
                    latest_index = (inlet.ptr - 1) % Config.BUFFER_SIZE
                    sample = inlet.buffers[latest_index]
                    streams_out.append(
                        {
                            "name": inlet.stream_name,
                            "stype": (inlet.stream_type or "").upper(),
                            "channels": inlet.channel_info["labels"],
                            "srate": inlet.sample_rate,
                            "data": sample.tolist(),
                        }
                    )

                frame = {
                    "type": "sample",
                    "t_server": time.time(),
                    "config": {
                        "max_samples": Config.MAX_SAMPLES,
                        "timer_interval_ms": Config.TIMER_INTERVAL,
                    },
                    "streams": streams_out,
                }
                payload = json.dumps(frame, separators=(",", ":"))

                for ws in list(self.clients):
                    try:
                        await ws.send(payload)
                    except Exception:
                        try:
                            self.clients.remove(ws)
                        except ValueError:
                            pass

            if self._stop_event and self._stop_event.is_set():
                break
            elapsed = time.time() - started_at
            await asyncio.sleep(max(0.0, self.interval_ms / 1000 - elapsed))


async def ws_handler(
    websocket: WebSocketConnection,
    broadcaster: Broadcaster,
    presenter: MainAppPresenter,
) -> None:
    """Handles WebSocket connection lifecycle and incoming messages.

    Registers client with broadcaster, processes discover_streams requests,
    and unregisters client on disconnect.
    """
    broadcaster.clients.append(websocket)
    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                if data.get("type") == "discover_streams":
                    print("[web] Client requested stream discovery...")

                    from MoBI_View.core.discovery import discover_and_create_inlets

                    new_inlets, count = await asyncio.to_thread(
                        discover_and_create_inlets,
                        Config.RESOLVE_WAIT,
                        presenter.data_inlets,
                    )

                    presenter.data_inlets.extend(new_inlets)

                    response = {
                        "type": "discover_result",
                        "count": count,
                        "total_streams": len(presenter.data_inlets),
                    }
                    await websocket.send(json.dumps(response))
            except json.JSONDecodeError:
                print(f"[web] Invalid JSON from client: {message}")
            except Exception as e:
                print(f"[web] Error handling message: {e}")
    finally:
        broadcaster.clients.remove(websocket)


def build_static_handler(static_dir: Path) -> Callable[..., SimpleHTTPRequestHandler]:
    """Returns HTTP handler that serves static files with no-cache headers."""

    class NoCacheHandler(SimpleHTTPRequestHandler):
        def end_headers(self) -> None:
            self.send_header(
                "Cache-Control",
                "no-store, no-cache, must-revalidate, max-age=0",
            )
            self.send_header("Pragma", "no-cache")
            super().end_headers()

    return partial(NoCacheHandler, directory=str(static_dir))


def start_http_static_server(host: str, port: int) -> None:
    """Starts HTTP server for static files in daemon thread."""
    static_dir = Path(__file__).parent / "static"
    handler = build_static_handler(static_dir)
    server = TCPServer((host, port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"[web] Static HTTP server running on http://{host}:{port}")


async def start_server(
    presenter: MainAppPresenter,
    stop_event: asyncio.Event | None = None,
) -> None:
    """Starts WebSocket server and broadcaster."""
    broadcaster = Broadcaster(
        presenter,
        stop_event=stop_event,
    )
    await broadcaster.start()

    handler = partial(ws_handler, broadcaster=broadcaster, presenter=presenter)
    async with websocket_serve(handler, Config.WS_HOST, Config.WS_PORT):
        print(
            f"[web] WebSocket server running on ws://{Config.WS_HOST}:{Config.WS_PORT}"
        )
        if stop_event:
            await stop_event.wait()
        else:
            await asyncio.Future()  # run forever


async def poll_presenter_continuously(
    presenter: MainAppPresenter,
    stop_event: asyncio.Event | None = None,
) -> None:
    """Polls presenter.poll_data() at regular intervals."""
    while True:
        if stop_event and stop_event.is_set():
            break
        try:
            presenter.poll_data()
        except Exception as e:
            print(f"[web] Error during polling: {e}")
        await asyncio.sleep(Config.POLL_INTERVAL)


async def run_server(presenter: MainAppPresenter) -> None:
    """Runs HTTP server, WebSocket server, and polling task."""
    start_http_static_server(Config.HTTP_HOST, Config.HTTP_PORT)

    await asyncio.gather(
        poll_presenter_continuously(presenter),
        start_server(presenter),
    )
