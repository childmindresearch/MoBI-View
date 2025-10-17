"""Unit tests for the async web server orchestration helpers."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from pathlib import Path
from typing import cast
from unittest.mock import MagicMock

import numpy as np
import pytest
from pytest_mock import MockFixture

from MoBI_View.web import server


@pytest.fixture
def stream_info_factory(mocker: MockFixture) -> Callable[..., MagicMock]:
    """Return a factory that builds mock StreamInfo objects."""

    def factory(**overrides: object) -> MagicMock:
        overrides_dict: dict[str, object] = dict(overrides)
        info = mocker.MagicMock()
        info.uid.return_value = overrides_dict.get("uid", "test-uid-123")
        info.name.return_value = overrides_dict.get("name", "TestStream")
        info.type.return_value = overrides_dict.get("stype", "EEG")
        info.source_id.return_value = overrides_dict.get("source_id", "test-source")
        info.channel_count.return_value = overrides_dict.get("channel_count", 2)
        info.channel_format.return_value = overrides_dict.get(
            "channel_format", "float32"
        )
        info.nominal_srate.return_value = overrides_dict.get("nominal_srate", 128.0)
        info.get_channel_labels.return_value = overrides_dict.get(
            "labels", ["Ch1", "Ch2"]
        )
        info.get_channel_types.return_value = overrides_dict.get(
            "channel_types", ["EEG", "EEG"]
        )
        info.get_channel_units.return_value = overrides_dict.get(
            "units", ["uV", "uV"]
        )
        return info

    return factory


@pytest.fixture
def inlet_factory(
    mocker: MockFixture, stream_info_factory: Callable[..., MagicMock]
) -> Callable[..., MagicMock]:
    """Return a factory that builds mock DataInlet objects."""

    def factory(**overrides: object) -> MagicMock:
        overrides_dict: dict[str, object] = dict(overrides)
        info = cast(MagicMock, overrides_dict.pop("info", stream_info_factory()))
        default_buffers = np.array([[0.0, 0.0], [1.0, 2.0], [0.0, 0.0]], dtype=float)
        buffers = np.asarray(
            overrides_dict.pop("buffers", default_buffers),
            dtype=float,
        )
        channel_info = cast(
            dict[str, object],
            overrides_dict.pop("channel_info", {"labels": ["Ch1", "Ch2"]}),
        )
        inlet = mocker.MagicMock()
        inlet.stream_name = overrides_dict.pop("stream_name", "TestStream")
        inlet.stream_type = overrides_dict.pop("stream_type", "eeg")
        inlet.channel_count = overrides_dict.pop("channel_count", 2)
        inlet.channel_info = channel_info
        inlet.sample_rate = overrides_dict.pop("sample_rate", 128.0)
        inlet.buffers = buffers
        inlet.ptr = overrides_dict.pop("ptr", buffers.shape[0] - 1)
        inlet.info.return_value = info
        for attr, value in overrides_dict.items():
            setattr(inlet, attr, value)
        return inlet

    return factory


@pytest.fixture
def mock_inlet(inlet_factory: Callable[..., MagicMock]) -> MagicMock:
    """Create a reusable mock inlet with defaults suitable for most tests."""
    return inlet_factory()


@pytest.fixture
def mock_registry(mocker: MockFixture, mock_inlet: MagicMock) -> MagicMock:
    """Create a mock Registry that returns test inlets."""
    registry = mocker.MagicMock(spec=server.Registry)
    registry.all.return_value = [mock_inlet]
    return registry


def test_stream_key_with_uid(
    stream_info_factory: Callable[..., MagicMock]
) -> None:
    """stream_key should prefer uid when available."""
    info = stream_info_factory(uid="abc123")
    assert server.stream_key(info) == "abc123"


def test_stream_key_fallback(
    stream_info_factory: Callable[..., MagicMock]
) -> None:
    """stream_key should build composite key when uid is empty."""
    info = stream_info_factory(uid="", source_id="src", name="Stream", stype="EEG")
    assert server.stream_key(info) == "src::Stream::EEG"


def test_stream_key_handles_uid_exception(
    stream_info_factory: Callable[..., MagicMock]
) -> None:
    """stream_key should fallback when uid() raises exception."""
    info = stream_info_factory(source_id="src", name="Test", stype="EEG")
    info.uid.side_effect = RuntimeError("error")
    assert server.stream_key(info) == "src::Test::EEG"


def test_stream_key_handles_attribute_exceptions(
    stream_info_factory: Callable[..., MagicMock]
) -> None:
    """stream_key should use fallback when attributes raise exceptions."""
    info = stream_info_factory(uid="")
    info.source_id.side_effect = RuntimeError("error")
    info.name.side_effect = RuntimeError("error")
    info.type.side_effect = RuntimeError("error")
    assert server.stream_key(info) == "?::?::?"


@pytest.mark.asyncio
async def test_ws_handler_manages_client(
    mocker: MockFixture, mock_registry: MagicMock
) -> None:
    """ws_handler should add and remove clients correctly."""
    broadcaster = server.Broadcaster(
        mock_registry, interval_ms=5, stop_event=asyncio.Event()
    )

    ws = mocker.MagicMock()
    ws.wait_closed = mocker.AsyncMock()
    assert ws not in broadcaster.clients
    await server.ws_handler(ws, broadcaster)
    assert ws not in broadcaster.clients


def test_run_web_creates_registry(mocker: MockFixture) -> None:
    """run_web should instantiate Registry and call _main."""
    fake_run = mocker.patch.object(server.asyncio, "run")
    server.run_web()

    fake_run.assert_called_once()
    coro = fake_run.call_args[0][0]
    assert coro.cr_code.co_name == "_main"
    coro.close()


@pytest.mark.asyncio
async def test_main_starts_services(mocker: MockFixture) -> None:
    """_main should start HTTP server and launch async services."""
    fake_http = mocker.patch.object(server, "start_http_static_server")
    fake_acq = mocker.patch.object(
        server, "start_acquisition", new=mocker.AsyncMock()
    )
    fake_srv = mocker.patch.object(server, "start_server", new=mocker.AsyncMock())

    mocker.patch.object(server.Config, "HTTP_HOST", "127.0.0.1")
    mocker.patch.object(server.Config, "HTTP_PORT", 9000)

    registry = server.Registry()
    await server._main(registry)

    fake_http.assert_called_once_with("127.0.0.1", 9000)
    fake_acq.assert_awaited_once()
    fake_srv.assert_awaited_once()


def test_build_static_handler_with_directory(mocker: MockFixture) -> None:
    """build_static_handler should return handler with directory parameter."""
    test_dir = mocker.MagicMock(spec=Path)
    handler = server.build_static_handler(test_dir)

    assert handler is not None
    assert callable(handler)



def test_broadcaster_uses_default_interval(mock_registry: MagicMock) -> None:
    """Broadcaster should use Config.TIMER_INTERVAL when interval_ms is None."""
    broadcaster = server.Broadcaster(mock_registry, interval_ms=None)
    
    from MoBI_View.core.config import Config
    assert broadcaster.interval_ms == Config.TIMER_INTERVAL


@pytest.mark.asyncio
async def test_broadcaster_start_creates_event(mock_registry: MagicMock) -> None:
    """Broadcaster.start should create stop_event if not provided."""
    broadcaster = server.Broadcaster(mock_registry, interval_ms=5)
    
    assert broadcaster._stop_event is None
    await broadcaster.start()
    assert broadcaster._stop_event is not None
    assert broadcaster._task is not None
    
    # Clean up
    broadcaster.stop()
    try:
        await broadcaster._task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_broadcaster_run_loop_stops(mock_registry: MagicMock) -> None:
    """Broadcaster._run should exit when stop_event is set."""
    stop_event = asyncio.Event()
    broadcaster = server.Broadcaster(
        mock_registry, interval_ms=5, stop_event=stop_event
    )
    
    # Start the run loop in background
    task = asyncio.create_task(broadcaster._run())
    await asyncio.sleep(0.01)  # Let it run once
    
    # Stop it
    stop_event.set()
    await task


@pytest.mark.asyncio
async def test_broadcaster_run_sends_frames(
    mocker: MockFixture, mock_registry: MagicMock
) -> None:
    """Broadcaster._run should send frames to clients."""
    stop_event = asyncio.Event()
    broadcaster = server.Broadcaster(
        mock_registry, interval_ms=5, stop_event=stop_event
    )
    
    # Add a mock client
    ws = mocker.MagicMock()
    ws.send = mocker.AsyncMock()
    broadcaster.clients.append(ws)
    
    # Run briefly
    task = asyncio.create_task(broadcaster._run())
    await asyncio.sleep(0.02)  # Allow at least one frame
    stop_event.set()
    await task
    
    # Should have sent at least one frame
    assert ws.send.await_count >= 1


@pytest.mark.asyncio
async def test_broadcaster_run_skips_empty_inlets(
    mocker: MockFixture, inlet_factory: Callable[..., MagicMock]
) -> None:
    """Broadcaster._run should skip inlets with ptr == 0."""
    stop_event = asyncio.Event()
    empty_inlet = inlet_factory(ptr=0)
    registry = mocker.MagicMock()
    registry.all.return_value = [empty_inlet]
    
    broadcaster = server.Broadcaster(
        registry, interval_ms=5, stop_event=stop_event
    )
    
    ws = mocker.MagicMock()
    ws.send = mocker.AsyncMock()
    broadcaster.clients.append(ws)
    
    task = asyncio.create_task(broadcaster._run())
    await asyncio.sleep(0.02)
    stop_event.set()
    await task
    
    # Should still send but with empty streams list
    assert ws.send.await_count >= 1
    calls = ws.send.call_args_list
    for call in calls:
        import json
        frame = json.loads(call[0][0])
        assert frame["streams"] == []


@pytest.mark.asyncio
async def test_broadcaster_run_forwards_channel_labels(
    mocker: MockFixture, inlet_factory: Callable[..., MagicMock]
) -> None:
    """Broadcaster._run should forward channel labels from the inlet."""
    stop_event = asyncio.Event()
    inlet = inlet_factory(channel_info={"labels": ["A", "B"]}, channel_count=2)
    registry = mocker.MagicMock()
    registry.all.return_value = [inlet]

    broadcaster = server.Broadcaster(
        registry, interval_ms=5, stop_event=stop_event
    )

    ws = mocker.MagicMock()
    ws.send = mocker.AsyncMock()
    broadcaster.clients.append(ws)

    task = asyncio.create_task(broadcaster._run())
    await asyncio.sleep(0.02)
    stop_event.set()
    await task

    assert ws.send.await_count >= 1
    calls = ws.send.call_args_list
    for call in calls:
        import json

        frame = json.loads(call[0][0])
        if frame["streams"]:
            assert frame["streams"][0]["channels"] == ["A", "B"]


@pytest.mark.asyncio
async def test_broadcaster_run_removes_failed_clients(
    mocker: MockFixture, mock_registry: MagicMock
) -> None:
    """Broadcaster._run should remove clients that fail during send."""
    stop_event = asyncio.Event()
    broadcaster = server.Broadcaster(
        mock_registry, interval_ms=5, stop_event=stop_event
    )
    
    # Add a failing client
    ws = mocker.MagicMock()
    ws.send = mocker.AsyncMock(side_effect=RuntimeError("closed"))
    broadcaster.clients.append(ws)
    
    # Run briefly
    task = asyncio.create_task(broadcaster._run())
    await asyncio.sleep(0.02)
    stop_event.set()
    await task
    
    # Client should be removed
    assert ws not in broadcaster.clients


def test_broadcaster_stop_sets_event(mock_registry: MagicMock) -> None:
    """Broadcaster.stop should set stop_event."""
    stop_event = asyncio.Event()
    broadcaster = server.Broadcaster(
        mock_registry, interval_ms=5, stop_event=stop_event
    )
    
    assert not stop_event.is_set()
    broadcaster.stop()
    assert stop_event.is_set()


def test_broadcaster_stop_cancels_task(
    mocker: MockFixture, mock_registry: MagicMock
) -> None:
    """Broadcaster.stop should cancel running task."""
    task = mocker.MagicMock()
    task.cancel = mocker.MagicMock()
    
    broadcaster = server.Broadcaster(mock_registry, interval_ms=5)
    broadcaster._task = task
    
    broadcaster.stop()
    task.cancel.assert_called_once()


@pytest.mark.asyncio
async def test_start_http_static_server(mocker: MockFixture) -> None:
    """start_http_static_server should launch HTTP server in daemon thread."""
    fake_tcp = mocker.patch.object(server, "TCPServer")
    fake_thread = mocker.patch.object(server.threading, "Thread")
    
    server.start_http_static_server("127.0.0.1", 8080)
    
    fake_tcp.assert_called_once()
    fake_thread.assert_called_once()
    assert fake_thread.call_args[1]["daemon"] is True


@pytest.mark.asyncio
async def test_start_server_uses_config_defaults(mocker: MockFixture) -> None:
    """start_server should rely on Config for host, port, and interval."""
    stop_event = asyncio.Event()
    stop_event.set()  # Stop immediately
    
    registry = server.Registry()
    mocker.patch.object(server.Config, "TIMER_INTERVAL", 10)
    mocker.patch.object(server.Config, "WS_HOST", "127.0.0.1")
    mocker.patch.object(server.Config, "WS_PORT", 9999)
    
    # Mock websocket_serve to avoid actual server start
    fake_serve = mocker.MagicMock()
    fake_serve.__aenter__ = mocker.AsyncMock()
    fake_serve.__aexit__ = mocker.AsyncMock()
    mocker.patch.object(server, "websocket_serve", return_value=fake_serve)
    
    await server.start_server(registry, stop_event=stop_event)
    
    server.websocket_serve.assert_called_once()
    args = server.websocket_serve.call_args
    assert args[0][1] == "127.0.0.1"
    assert args[0][2] == 9999


@pytest.mark.asyncio
async def test_start_acquisition_single_pass(
    mocker: MockFixture,
    capsys: pytest.CaptureFixture[str],
    stream_info_factory: Callable[..., MagicMock],
    inlet_factory: Callable[..., MagicMock],
) -> None:
    """start_acquisition should handle single-pass mode with resolve_interval <= 0."""
    stop_event = asyncio.Event()
    registry = server.Registry()
    info = stream_info_factory()

    async def resolve(*_args: object, **_kwargs: object) -> list[MagicMock]:
        return [info]

    mocker.patch.object(server.asyncio, "to_thread", side_effect=resolve)
    mocker.patch.object(server.Config, "RESOLVE_INTERVAL", 0.0)
    mocker.patch.object(server, "DataInlet", return_value=inlet_factory())

    task = asyncio.create_task(server.start_acquisition(registry, stop_event))
    await asyncio.sleep(0.05)
    stop_event.set()
    await task

    captured = capsys.readouterr()
    assert "single-pass" in captured.out
    assert info.name.return_value in captured.out


@pytest.mark.asyncio
async def test_start_acquisition_continuous_mode(
    mocker: MockFixture,
    capsys: pytest.CaptureFixture[str],
    stream_info_factory: Callable[..., MagicMock],
    inlet_factory: Callable[..., MagicMock],
) -> None:
    """start_acquisition should continuously discover streams when interval > 0."""
    stop_event = asyncio.Event()
    registry = server.Registry()
    info = stream_info_factory()
    call_count = 0

    async def resolve(*_args: object, **_kwargs: object) -> list[MagicMock]:
        nonlocal call_count
        call_count += 1
        if call_count >= 2:
            stop_event.set()
        return [info]

    mocker.patch.object(server.asyncio, "to_thread", side_effect=resolve)
    mocker.patch.object(server.Config, "RESOLVE_INTERVAL", 0.01)
    mocker.patch.object(server, "DataInlet", return_value=inlet_factory())

    await server.start_acquisition(registry, stop_event)

    captured = capsys.readouterr()
    assert "Discovered stream" in captured.out


@pytest.mark.asyncio
async def test_start_acquisition_handles_stream_lost(
    mocker: MockFixture,
    capsys: pytest.CaptureFixture[str],
    stream_info_factory: Callable[..., MagicMock],
    inlet_factory: Callable[..., MagicMock],
) -> None:
    """start_acquisition should handle StreamLostError and remove inlet."""
    stop_event = asyncio.Event()
    registry = server.Registry()
    info = stream_info_factory()

    async def resolve(*_args: object, **_kwargs: object) -> list[MagicMock]:
        return [info]

    mocker.patch.object(server.asyncio, "to_thread", side_effect=resolve)
    mocker.patch.object(server.Config, "RESOLVE_INTERVAL", 0.0)

    lost_inlet = inlet_factory()
    lost_inlet.pull_sample.side_effect = server.StreamLostError("lost")
    mocker.patch.object(server, "DataInlet", return_value=lost_inlet)

    task = asyncio.create_task(server.start_acquisition(registry, stop_event))
    await asyncio.sleep(0.05)
    stop_event.set()
    await task

    captured = capsys.readouterr()
    assert "Stream lost" in captured.out


@pytest.mark.asyncio
async def test_start_acquisition_handles_generic_exception(
    mocker: MockFixture,
    stream_info_factory: Callable[..., MagicMock],
    inlet_factory: Callable[..., MagicMock],
) -> None:
    """start_acquisition should handle generic exceptions in poll_loop."""
    stop_event = asyncio.Event()
    registry = server.Registry()
    info = stream_info_factory()
    call_count = 0

    async def resolve(*_args: object, **_kwargs: object) -> list[MagicMock]:
        nonlocal call_count
        call_count += 1
        if call_count > 1:
            stop_event.set()
        return [info]

    mocker.patch.object(server.asyncio, "to_thread", side_effect=resolve)
    mocker.patch.object(server.Config, "RESOLVE_INTERVAL", 0.0)

    pull_count = 0

    def fake_pull() -> None:
        nonlocal pull_count
        pull_count += 1
        if pull_count == 1:
            raise RuntimeError("generic error")
        stop_event.set()

    err_inlet = inlet_factory()
    err_inlet.pull_sample = fake_pull
    mocker.patch.object(server, "DataInlet", return_value=err_inlet)

    await server.start_acquisition(registry, stop_event)

    assert pull_count >= 1


@pytest.mark.asyncio
async def test_start_acquisition_deduplicates_streams(
    mocker: MockFixture,
    stream_info_factory: Callable[..., MagicMock],
    inlet_factory: Callable[..., MagicMock],
) -> None:
    """start_acquisition should not create duplicate inlets for same stream."""
    stop_event = asyncio.Event()
    registry = server.Registry()
    info = stream_info_factory()
    call_count = 0

    async def resolve(*_args: object, **_kwargs: object) -> list[MagicMock]:
        nonlocal call_count
        call_count += 1
        if call_count > 2:
            stop_event.set()
        return [info]

    mocker.patch.object(server.asyncio, "to_thread", side_effect=resolve)
    mocker.patch.object(server.Config, "RESOLVE_INTERVAL", 0.01)

    inlet = inlet_factory()
    create_count = 0

    def new_inlet(*_args: object, **_kwargs: object) -> MagicMock:
        nonlocal create_count
        create_count += 1
        return inlet

    mocker.patch.object(server, "DataInlet", side_effect=new_inlet)

    await server.start_acquisition(registry, stop_event)

    assert create_count == 1
