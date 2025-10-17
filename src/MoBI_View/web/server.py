"""WebSocket server that publishes recent LSL samples to the browser UI."""

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
from pylsl import StreamInfo, resolve_streams

from MoBI_View.core.config import Config
from MoBI_View.core.data_inlet import DataInlet
from MoBI_View.core.exceptions import StreamLostError
from MoBI_View.web.stream_buffers import Registry

try:
    import websockets.asyncio.server as websockets_server
except ImportError:  # pragma: no cover - legacy fallback for websockets<14
    websockets_server = getattr(websockets, "server")  # type: ignore[attr-defined]

websocket_serve: Any = getattr(websockets_server, "serve")  # type: ignore[attr-defined]

WebSocketConnection = Any


def build_static_handler(static_dir: Path) -> Callable[..., SimpleHTTPRequestHandler]:
    """Return an HTTP request handler that enforces no-cache headers."""

    class NoCacheHandler(SimpleHTTPRequestHandler):
        def end_headers(self) -> None:
            self.send_header(
                "Cache-Control",
                "no-store, no-cache, must-revalidate, max-age=0",
            )
            self.send_header("Pragma", "no-cache")
            super().end_headers()

    return partial(NoCacheHandler, directory=str(static_dir))


def stream_key(info: StreamInfo) -> str:
    """Return a stable identifier for an LSL stream."""
    try:
        uid = info.uid()
        if uid:
            return str(uid)
    except Exception:
        pass

    parts: list[str] = []
    for attr in ("source_id", "name", "type"):
        method = getattr(info, attr, None)
        if not callable(method):
            parts.append("?")
            continue
        try:
            value = method()
        except Exception:
            value = None
        parts.append(str(value) if value else "?")
    return "::".join(parts)


class Broadcaster:
    """Periodically publish buffered LSL samples to connected clients."""

    def __init__(
        self,
        registry: Registry,
        interval_ms: int | None = None,
        stop_event: asyncio.Event | None = None,
    ) -> None:
        """Initialize broadcaster with registry and interval."""
        self.registry = registry
        self.interval_ms = interval_ms or Config.TIMER_INTERVAL
        self.clients: list[WebSocketConnection] = []
        self._task: asyncio.Task | None = None
        self._stop_event = stop_event

    async def start(self) -> None:
        """Launch the background frame publishing loop."""
        if self._stop_event is None:
            self._stop_event = asyncio.Event()
        self._task = asyncio.create_task(self._run())

    def stop(self) -> None:
        """Signal the background loop to exit and cancel the task if needed."""
        if self._stop_event is not None:
            self._stop_event.set()
        if self._task is not None:
            self._task.cancel()

    async def _run(self) -> None:
        """Continuously broadcast the newest sample from each active inlet.

        The coroutine loops at roughly ``self.interval_ms`` cadence. Each cycle
        performs the following steps:

        1. Collect the most recent sample from every registered inlet that has
           produced data.
        2. Serialize the aggregated stream snapshot into a compact JSON payload
           that also carries basic timing/configuration metadata for the client.
        3. Deliver the payload to all connected WebSocket clients, pruning any
           connection that fails during transmission.

        The loop terminates when ``self._stop_event`` is set (for example during
        shutdown or from a test harness).
        """
        while True:
            started_at = time.time()
            if self.clients:
                streams_out: list[dict[str, Any]] = []
                for inlet in self.registry.all():
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


async def ws_handler(websocket: WebSocketConnection, broadcaster: Broadcaster) -> None:
    """Manage the lifecycle of a WebSocket connection.

    Args:
        websocket: Active WebSocket connection.
        broadcaster: Broadcaster that produces frames.
    """
    broadcaster.clients.append(websocket)
    try:
        await websocket.wait_closed()
    finally:
        try:
            broadcaster.clients.remove(websocket)
        except ValueError:
            pass


async def start_server(
    registry: Registry, stop_event: asyncio.Event | None = None
) -> None:
    """Start the WebSocket server and frame broadcaster.

    Args:
        registry: Registry that provides data inlets.
        stop_event: Optional event used to request shutdown (mainly for tests).
    """
    broadcaster = Broadcaster(
        registry,
        stop_event=stop_event,
    )
    await broadcaster.start()

    async def handler(ws: WebSocketConnection) -> None:
        return await ws_handler(ws, broadcaster)

    host = Config.WS_HOST
    port = Config.WS_PORT
    try:
        async with websocket_serve(handler, host, port, max_queue=1):
            if stop_event is None:
                await asyncio.Event().wait()
            else:
                await stop_event.wait()
    finally:
        broadcaster.stop()


def start_http_static_server(host: str = "0.0.0.0", port: int = 8000) -> None:
    """Serve the viewer static files on an HTTP port in a background thread.

    Args:
        host: Host interface to bind.
        port: HTTP port to expose.
    """
    static_dir = Path(__file__).parent / "static"
    handler = build_static_handler(static_dir)
    httpd = TCPServer((host, port), handler)

    def _serve() -> None:
        with httpd:
            httpd.serve_forever()

    threading.Thread(target=_serve, daemon=True).start()


async def start_acquisition(
    registry: Registry, stop_event: asyncio.Event | None = None
) -> None:
    """Discover LSL streams and launch polling tasks for each one.

    Args:
        registry: Registry that stores active data inlets.
        stop_event: Optional event used to request shutdown (mainly for tests).
    """
    seen: set[str] = set()
    poll_tasks: set[asyncio.Task] = set()
    resolve_interval = Config.RESOLVE_INTERVAL
    resolve_wait = Config.RESOLVE_WAIT

    async def poll_inlet(inlet: DataInlet) -> None:
        while True:
            if stop_event and stop_event.is_set():
                break
            try:
                inlet.pull_sample()
            except StreamLostError:
                print(f"[web] Stream lost for {inlet.stream_name}; removing inlet")
                registry.remove(inlet.stream_name)
                break
            except Exception:
                await asyncio.sleep(0.05)
            await asyncio.sleep(Config.POLL_INTERVAL)

    async def process_discovered(infos: list[StreamInfo]) -> None:
        for info in infos:
            key = stream_key(info)
            if key in seen:
                continue
            seen.add(key)
            try:
                inlet = DataInlet(info)
                print(
                    f"[web] Discovered stream: name={inlet.stream_name} "
                    f"type={(inlet.stream_type or '').upper()} "
                    f"channels={inlet.channel_count} srate={inlet.sample_rate}"
                )
                registry.add(inlet)
                task = asyncio.create_task(poll_inlet(inlet))
                poll_tasks.add(task)
                task.add_done_callback(lambda t: poll_tasks.discard(t))
            except Exception as exc:  # pragma: no cover
                try:
                    name = info.name() if callable(getattr(info, "name", None)) else "?"
                except Exception:
                    name = "?"
                print(f"[web] Error starting inlet for stream '{name}': {exc}")

    # Single-pass mode
    if resolve_interval <= 0:
        infos = list(await asyncio.to_thread(resolve_streams, wait_time=resolve_wait))
        print(f"[web] resolve_streams -> {len(infos)} streams (single-pass)")
        await process_discovered(infos)
        if stop_event:
            await stop_event.wait()
        else:
            await asyncio.Event().wait()
        if poll_tasks:
            await asyncio.gather(*poll_tasks, return_exceptions=True)
        return

    # Continuous discovery mode
    last_count = -1
    while True:
        if stop_event and stop_event.is_set():
            break
        infos = list(await asyncio.to_thread(resolve_streams, wait_time=resolve_wait))
        if len(infos) != last_count:
            print(f"[web] resolve_streams -> {len(infos)} streams")
            last_count = len(infos)
        await process_discovered(infos)
        if stop_event:
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=resolve_interval)
            except asyncio.TimeoutError:
                continue
        else:
            await asyncio.sleep(resolve_interval)
    if poll_tasks:
        await asyncio.gather(*poll_tasks, return_exceptions=True)


def run_web() -> None:
    """Run the web acquisition and WebSocket server."""
    registry = Registry()
    asyncio.run(_main(registry))


async def _main(reg: Registry) -> None:
    """Start auxiliary services and await acquisition tasks.

    Args:
        reg: Registry that will hold stream buffers for the session.
    """
    start_http_static_server(Config.HTTP_HOST, Config.HTTP_PORT)
    await asyncio.gather(start_acquisition(reg), start_server(reg))
