"""Unit tests for the Broadcaster class."""

import asyncio
import json
import time
from unittest.mock import MagicMock, patch

import pytest

from MoBI_View.core import config
from MoBI_View.presenters import main_app_presenter
from MoBI_View.web import broadcaster


async def _async_noop(msg: str) -> None:
    """Async no-op for mocking successful client.send()."""


async def _async_raise_connection_error(msg: str) -> None:
    """Async function that raises ConnectionError for mocking failed send."""
    raise ConnectionError("Disconnected")


@pytest.fixture
def mock_presenter() -> MagicMock:
    """Creates a mock MainAppPresenter."""
    mock = MagicMock(spec=main_app_presenter.MainAppPresenter)
    mock.poll_data.return_value = []
    return mock


@pytest.fixture
def broadcaster_instance(mock_presenter: MagicMock) -> broadcaster.Broadcaster:
    """Creates an unstarted Broadcaster instance."""
    return broadcaster.Broadcaster(presenter=mock_presenter, broadcast_interval=0.01)


def test_init_sets_presenter_and_defaults(
    broadcaster_instance: broadcaster.Broadcaster,
    mock_presenter: MagicMock,
) -> None:
    """Tests __init__ sets presenter and initializes default state."""
    assert broadcaster_instance.presenter is mock_presenter
    assert broadcaster_instance.clients == set()
    assert broadcaster_instance._running is False
    assert broadcaster_instance._thread is None
    assert broadcaster_instance._loop is None


def test_init_uses_default_broadcast_interval_from_config(
    mock_presenter: MagicMock,
) -> None:
    """Tests __init__ uses Config.TIMER_INTERVAL when no interval provided."""
    expected_interval = config.Config.TIMER_INTERVAL / 1000

    bc = broadcaster.Broadcaster(presenter=mock_presenter)

    assert bc.broadcast_interval == expected_interval


def test_init_uses_custom_broadcast_interval_when_provided(
    mock_presenter: MagicMock,
) -> None:
    """Tests __init__ uses custom interval when provided."""
    custom_interval = 0.1

    bc = broadcaster.Broadcaster(
        presenter=mock_presenter,
        broadcast_interval=custom_interval,
    )

    assert bc.broadcast_interval == custom_interval


def test_start_sets_running_and_creates_thread(
    broadcaster_instance: broadcaster.Broadcaster,
) -> None:
    """Tests start() sets _running=True and creates a daemon thread."""
    broadcaster_instance.start()

    assert broadcaster_instance._running is True
    assert broadcaster_instance._thread is not None
    assert broadcaster_instance._thread.daemon is True

    broadcaster_instance.stop()


def test_start_when_already_running_logs_warning_and_does_nothing(
    broadcaster_instance: broadcaster.Broadcaster,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Tests start(), when already running, logs warning and keeps same thread."""
    broadcaster_instance.start()
    original_thread = broadcaster_instance._thread

    broadcaster_instance.start()

    assert broadcaster_instance._thread is original_thread
    assert "already running" in caplog.text

    broadcaster_instance.stop()


def test_stop_when_not_running_logs_warning_and_returns(
    broadcaster_instance: broadcaster.Broadcaster,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Tests stop(), when _running=False, logs warning and returns early."""
    broadcaster_instance.stop()

    assert "not running" in caplog.text


def test_stop_when_thread_is_none_returns_early(
    broadcaster_instance: broadcaster.Broadcaster,
) -> None:
    """Tests stop() returns early when _thread is None."""
    broadcaster_instance._running = True
    broadcaster_instance._thread = None
    broadcaster_instance._loop = MagicMock()

    broadcaster_instance.stop()

    assert broadcaster_instance._running is False
    assert broadcaster_instance._loop is not None


def test_stop_joins_thread_and_cleans_up(
    broadcaster_instance: broadcaster.Broadcaster,
) -> None:
    """Tests stop() joins thread and sets _thread and _loop to None."""
    broadcaster_instance.start()
    time.sleep(0.02)

    broadcaster_instance.stop()

    assert broadcaster_instance._running is False
    assert broadcaster_instance._thread is None
    assert broadcaster_instance._loop is None


def test_set_loop_assigns_loop(
    broadcaster_instance: broadcaster.Broadcaster,
) -> None:
    """Tests set_loop() stores the given event loop for scheduling sends."""
    loop = asyncio.new_event_loop()

    broadcaster_instance.set_loop(loop)

    assert broadcaster_instance._loop is loop
    loop.close()


def test_stop_calculates_timeout_from_clients(
    broadcaster_instance: broadcaster.Broadcaster,
) -> None:
    """Tests stop() calculates join timeout based on client count."""
    broadcaster_instance.start()
    time.sleep(0.02)
    mock_client1 = MagicMock()
    mock_client2 = MagicMock()
    broadcaster_instance.add_client(mock_client1)
    broadcaster_instance.add_client(mock_client2)

    broadcaster_instance.stop()

    assert broadcaster_instance._thread is None


def test_add_client_adds_to_clients_set(
    broadcaster_instance: broadcaster.Broadcaster,
) -> None:
    """Tests add_client() adds client to the clients set."""
    mock_client = MagicMock()

    broadcaster_instance.add_client(mock_client)

    assert mock_client in broadcaster_instance.clients
    assert len(broadcaster_instance.clients) == 1


def test_add_client_logs_client_count(
    broadcaster_instance: broadcaster.Broadcaster,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Tests add_client() logs the total client count."""
    mock_client = MagicMock()

    with caplog.at_level("INFO"):
        broadcaster_instance.add_client(mock_client)

    assert "total clients: 1" in caplog.text


def test_add_client_multiple_times_stores_once(
    broadcaster_instance: broadcaster.Broadcaster,
) -> None:
    """Tests adding the same client twice only stores it once."""
    mock_client = MagicMock()

    broadcaster_instance.add_client(mock_client)
    broadcaster_instance.add_client(mock_client)

    assert len(broadcaster_instance.clients) == 1


def test_add_client_multiple_different_clients(
    broadcaster_instance: broadcaster.Broadcaster,
) -> None:
    """Tests adding multiple different clients."""
    client1 = MagicMock()
    client2 = MagicMock()

    broadcaster_instance.add_client(client1)
    broadcaster_instance.add_client(client2)

    assert len(broadcaster_instance.clients) == 2
    assert client1 in broadcaster_instance.clients
    assert client2 in broadcaster_instance.clients


def test_remove_client_removes_from_set_and_logs_count(
    broadcaster_instance: broadcaster.Broadcaster,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Tests remove_client() removes client from set and logs total count."""
    mock_client = MagicMock()
    broadcaster_instance.add_client(mock_client)

    with caplog.at_level("INFO"):
        broadcaster_instance.remove_client(mock_client)

    assert mock_client not in broadcaster_instance.clients
    assert len(broadcaster_instance.clients) == 0
    assert "total clients: 0" in caplog.text


def test_remove_client_nonexistent_does_not_raise(
    broadcaster_instance: broadcaster.Broadcaster,
) -> None:
    """Tests remove_client() with nonexistent client does not raise (discard)."""
    mock_client = MagicMock()

    broadcaster_instance.remove_client(mock_client)

    assert len(broadcaster_instance.clients) == 0


def test_format_frame_empty_streams_returns_valid_json(
    broadcaster_instance: broadcaster.Broadcaster,
) -> None:
    """Tests format_frame() with empty list returns valid JSON with streams key."""
    result = broadcaster_instance.format_frame([])
    parsed = json.loads(result)

    assert "streams" in parsed
    assert parsed["streams"] == []


def test_format_frame_single_stream(
    broadcaster_instance: broadcaster.Broadcaster,
) -> None:
    """Tests format_frame() with single stream data."""
    streams_data = [
        {
            "stream_name": "EEG",
            "data": [1.0, 2.0, 3.0],
            "channel_labels": ["Fp1", "Fp2", "Fz"],
        }
    ]

    result = broadcaster_instance.format_frame(streams_data)
    parsed = json.loads(result)

    assert len(parsed["streams"]) == 1
    assert parsed["streams"][0]["stream_name"] == "EEG"
    assert parsed["streams"][0]["data"] == [1.0, 2.0, 3.0]
    assert parsed["streams"][0]["channel_labels"] == ["Fp1", "Fp2", "Fz"]


def test_format_frame_multiple_streams(
    broadcaster_instance: broadcaster.Broadcaster,
) -> None:
    """Tests format_frame() with multiple streams."""
    streams_data = [
        {
            "stream_name": "EEG",
            "data": [1.0, 2.0, 3.0],
            "channel_labels": ["Fp1", "Fp2", "Fz"],
        },
        {
            "stream_name": "Accelerometer",
            "data": [0.1, 0.2, 9.8],
            "channel_labels": ["X", "Y", "Z"],
        },
    ]

    result = broadcaster_instance.format_frame(streams_data)

    parsed = json.loads(result)
    assert len(parsed["streams"]) == 2
    assert parsed["streams"][0]["stream_name"] == "EEG"
    assert parsed["streams"][1]["stream_name"] == "Accelerometer"


def test_run_logs_start_and_end(
    broadcaster_instance: broadcaster.Broadcaster,
    mock_presenter: MagicMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Tests _run() logs start/end without touching the externally-set loop."""
    broadcaster_instance._running = True

    def stop_after_one_iteration() -> None:
        broadcaster_instance._running = False

    mock_presenter.poll_data.side_effect = stop_after_one_iteration

    with caplog.at_level("INFO"):
        broadcaster_instance._run()

    assert "Broadcast loop started" in caplog.text
    assert "Broadcast loop ended" in caplog.text
    assert broadcaster_instance._loop is None


def test_run_polls_presenter_for_data(
    broadcaster_instance: broadcaster.Broadcaster,
    mock_presenter: MagicMock,
) -> None:
    """Tests _run() calls presenter.poll_data() each iteration."""
    call_count = 0

    def stop_after_three_iterations() -> list[object]:
        nonlocal call_count
        call_count += 1
        if call_count >= 3:
            broadcaster_instance._running = False
        return []

    broadcaster_instance._running = True
    mock_presenter.poll_data.side_effect = stop_after_three_iterations

    broadcaster_instance._run()

    assert mock_presenter.poll_data.call_count == 3


def test_run_broadcasts_when_data_available(
    broadcaster_instance: broadcaster.Broadcaster,
    mock_presenter: MagicMock,
) -> None:
    """Tests _run() calls _broadcast_to_clients when poll_data returns data."""
    streams_data: list[object] = [
        {"stream_name": "EEG", "data": [1.0], "channel_labels": ["Fp1"]}
    ]

    def return_data_then_stop() -> list[object]:
        broadcaster_instance._running = False
        return streams_data

    broadcaster_instance._running = True
    mock_presenter.poll_data.side_effect = return_data_then_stop

    with patch.object(broadcaster_instance, "_broadcast_to_clients") as mock_broadcast:
        broadcaster_instance._run()

        mock_broadcast.assert_called_once()
        call_arg = mock_broadcast.call_args[0][0]
        assert "EEG" in call_arg


def test_run_does_not_broadcast_when_no_data(
    broadcaster_instance: broadcaster.Broadcaster,
    mock_presenter: MagicMock,
) -> None:
    """Tests _run() does not call _broadcast_to_clients when poll_data is empty."""

    def return_empty_then_stop() -> list[object]:
        broadcaster_instance._running = False
        return []

    broadcaster_instance._running = True
    mock_presenter.poll_data.side_effect = return_empty_then_stop

    with patch.object(broadcaster_instance, "_broadcast_to_clients") as mock_broadcast:
        broadcaster_instance._run()

        mock_broadcast.assert_not_called()


def test_run_handles_exception_and_continues(
    broadcaster_instance: broadcaster.Broadcaster,
    mock_presenter: MagicMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Tests _run() logs error and continues when exception occurs."""
    call_count = 0

    def raise_then_stop() -> list[object]:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("Test error")
        broadcaster_instance._running = False
        return []

    broadcaster_instance._running = True
    mock_presenter.poll_data.side_effect = raise_then_stop

    broadcaster_instance._run()

    assert "Error in broadcast loop" in caplog.text
    assert call_count == 2


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_broadcast_to_clients_sends_to_all_clients(
    broadcaster_instance: broadcaster.Broadcaster,
) -> None:
    """Tests _broadcast_to_clients() sends message to all connected clients."""
    broadcaster_instance._loop = asyncio.new_event_loop()
    mock_client1 = MagicMock()
    mock_client2 = MagicMock()
    mock_client1.send = MagicMock(side_effect=_async_noop)
    mock_client2.send = MagicMock(side_effect=_async_noop)
    broadcaster_instance.add_client(mock_client1)
    broadcaster_instance.add_client(mock_client2)
    message = '{"streams": []}'

    broadcaster_instance._broadcast_to_clients(message)

    mock_client1.send.assert_called_once_with(message)
    mock_client2.send.assert_called_once_with(message)
    broadcaster_instance._loop.close()


def test_broadcast_to_clients_does_nothing_when_no_clients(
    broadcaster_instance: broadcaster.Broadcaster,
) -> None:
    """Tests _broadcast_to_clients() does nothing when no clients connected."""
    broadcaster_instance._loop = asyncio.new_event_loop()
    message = '{"streams": []}'

    broadcaster_instance._broadcast_to_clients(message)

    assert len(broadcaster_instance.clients) == 0
    broadcaster_instance._loop.close()


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_broadcast_to_clients_removes_disconnected_clients(
    broadcaster_instance: broadcaster.Broadcaster,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Tests _broadcast_to_clients() removes all clients that fail to receive."""
    broadcaster_instance._loop = asyncio.new_event_loop()
    mock_client1 = MagicMock()
    mock_client2 = MagicMock()
    mock_client1.send = MagicMock(side_effect=_async_raise_connection_error)
    mock_client2.send = MagicMock(side_effect=_async_raise_connection_error)
    broadcaster_instance.add_client(mock_client1)
    broadcaster_instance.add_client(mock_client2)
    message = '{"streams": []}'

    broadcaster_instance._broadcast_to_clients(message)

    mock_client1.send.assert_called_once_with(message)
    mock_client2.send.assert_called_once_with(message)
    assert mock_client1 not in broadcaster_instance.clients
    assert mock_client2 not in broadcaster_instance.clients
    assert len(broadcaster_instance.clients) == 0
    assert "Failed to send to client" in caplog.text
    broadcaster_instance._loop.close()


def test_broadcast_to_clients_does_nothing_when_loop_is_none(
    broadcaster_instance: broadcaster.Broadcaster,
) -> None:
    """Tests _broadcast_to_clients() does not send when _loop is None."""
    broadcaster_instance._loop = None
    mock_client = MagicMock()
    broadcaster_instance.add_client(mock_client)
    message = '{"streams": []}'

    broadcaster_instance._broadcast_to_clients(message)

    mock_client.send.assert_not_called()
    assert mock_client in broadcaster_instance.clients
