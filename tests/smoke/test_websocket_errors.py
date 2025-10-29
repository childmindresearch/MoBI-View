"""Smoke tests for WebSocket error handling."""

import asyncio
import json
from typing import Generator
from unittest.mock import patch

import pytest
import websockets
from pylsl import StreamInfo, StreamOutlet

from MoBI_View.core.config import Config
from MoBI_View.presenters.main_app_presenter import MainAppPresenter
from MoBI_View.web.server import start_server


@pytest.fixture
def test_stream() -> Generator[StreamOutlet, None, None]:
    """Creates test LSL stream for error handling tests."""
    info = StreamInfo("ErrorTestStream", "EEG", 2, 100, "float32", "error_test")
    outlet = StreamOutlet(info)
    yield outlet
    del outlet


@pytest.mark.asyncio
async def test_invalid_json_handled(test_stream: StreamOutlet) -> None:
    """Invalid JSON messages are logged without crashing server."""
    # Arrange
    presenter = MainAppPresenter(data_inlets=[])
    stop_event = asyncio.Event()
    server_task = asyncio.create_task(start_server(presenter, stop_event))
    await asyncio.sleep(0.1)

    try:
        async with websockets.connect(f"ws://127.0.0.1:{Config.WS_PORT}") as ws:
            # Act - send invalid JSON
            await ws.send("not valid json at all")
            await asyncio.sleep(0.1)

            # Act - send valid request after invalid JSON
            valid_request = json.dumps({"type": "discover_streams"})
            await ws.send(valid_request)

            # Skip any sample messages and wait for discover_result
            while True:
                response = await asyncio.wait_for(ws.recv(), timeout=2.0)
                result = json.loads(response)
                if result["type"] == "discover_result":
                    break

            # Assert - server handled invalid JSON and continued working
            assert result["type"] == "discover_result"
            assert "count" in result
    finally:
        stop_event.set()
        await server_task


@pytest.mark.asyncio
async def test_discovery_error_handled(test_stream: StreamOutlet) -> None:
    """Discovery errors are caught and server continues operating."""
    # Arrange
    presenter = MainAppPresenter(data_inlets=[])
    stop_event = asyncio.Event()

    def failing_discover(*args: object, **kwargs: object) -> None:
        raise RuntimeError("Simulated discovery failure")

    server_task = asyncio.create_task(start_server(presenter, stop_event))
    await asyncio.sleep(0.1)

    try:
        async with websockets.connect(f"ws://127.0.0.1:{Config.WS_PORT}") as ws:
            with patch(
                "MoBI_View.core.discovery.discover_and_create_inlets",
                side_effect=failing_discover,
            ):
                # Act - send discover request that will fail
                request = json.dumps({"type": "discover_streams"})
                await ws.send(request)
                await asyncio.sleep(0.15)

                # Assert - WebSocket connection stayed open, can send more messages
                ping_request = json.dumps({"type": "discover_streams"})
                await ws.send(ping_request)
                await asyncio.sleep(0.05)
    finally:
        stop_event.set()
        try:
            await asyncio.wait_for(server_task, timeout=1.0)
        except asyncio.TimeoutError:
            server_task.cancel()
