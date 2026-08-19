"""WebSocket broadcaster for real-time data streaming.

This module provides the Broadcaster class that reads data from the presenter
and broadcasts it as JSON frames to all connected WebSocket clients.
"""

import asyncio
import json
import logging
import threading
import time
from typing import Any, Dict, List, Optional, Set

from websockets.asyncio import server

from MoBI_View.core import config
from MoBI_View.presenters import main_app_presenter

logger = logging.getLogger("MoBI-View.web.broadcaster")


class Broadcaster:
    """Broadcasts real-time data from presenter to WebSocket clients.

    The Broadcaster runs a background thread that continuously polls the presenter
    for new data, formats it as JSON, and broadcasts to all connected clients.

    Attributes:
        presenter: The MainAppPresenter instance providing data.
        clients: Set of connected WebSocket clients.
        broadcast_interval: Time between broadcasts in seconds.
    """

    CLIENT_SEND_TIMEOUT: float = 1.0

    def __init__(
        self,
        presenter: main_app_presenter.MainAppPresenter,
        broadcast_interval: Optional[float] = None,
    ) -> None:
        """Initializes the Broadcaster with a presenter and interval.

        Args:
            presenter: The MainAppPresenter instance to poll for data.
            broadcast_interval: Time between broadcasts in seconds. Defaults to
                Config.TIMER_INTERVAL converted to seconds.
        """
        self.presenter = presenter
        self.clients: Set[server.ServerConnection] = set()
        self._clients_lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

        self.broadcast_interval = (
            broadcast_interval or config.Config.TIMER_INTERVAL / 1000
        )

    def start(self) -> None:
        """Starts the broadcast loop in a background thread.

        Creates a new thread running the broadcast loop. If already running,
        this method does nothing.
        """
        if self._running:
            logger.warning("Broadcaster already running")
            return

        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info("Broadcaster started")

    def stop(self) -> None:
        """Stops the broadcast loop and waits for thread termination.

        Signals the broadcast loop to stop and waits for the thread to finish.
        If not running, this method does nothing.
        """
        if not self._running:
            logger.warning("Broadcaster not running")
            return

        self._running = False
        if self._thread is None:
            return

        with self._clients_lock:
            client_count = len(self.clients)
        timeout = (
            self.broadcast_interval
            + (client_count * self.CLIENT_SEND_TIMEOUT)
            + self.CLIENT_SEND_TIMEOUT
        )
        self._thread.join(timeout=timeout)
        self._thread = None
        self._loop = None
        logger.info("Broadcaster stopped")

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Sets the event loop used to schedule client sends.

        Must be the loop actually running the WebSocket server, since
        client connections are bound to it. Scheduling coroutines on any
        other loop (e.g. one created in the broadcast thread but never
        driven) would leave them pending forever.

        Args:
            loop: The running asyncio event loop of the WebSocket server.
        """
        self._loop = loop

    def add_client(self, client: server.ServerConnection) -> None:
        """Adds a WebSocket client to the broadcast set.

        Args:
            client: The WebSocket connection to add.
        """
        with self._clients_lock:
            self.clients.add(client)
            logger.info("Client added, total clients: %d", len(self.clients))

    def remove_client(self, client: server.ServerConnection) -> None:
        """Removes a WebSocket client from the broadcast set.

        Args:
            client: The WebSocket connection to remove.
        """
        with self._clients_lock:
            self.clients.discard(client)
            logger.info("Client removed, total clients: %d", len(self.clients))

    def format_frame(self, streams_data: List[Dict[str, Any]]) -> str:
        """Formats stream data as a JSON frame for broadcasting.

        Creates a JSON structure containing timestamp and all stream data.

        Args:
            streams_data: List of stream data dictionaries from presenter.poll_data().
                Each dictionary contains 'stream_name', 'data', and 'channel_labels'.

        Returns:
            JSON string containing the formatted frame.
        """
        frame = {
            "streams": streams_data,
        }
        return json.dumps(frame)

    def _run(self) -> None:
        """Main broadcast loop running in background thread.

        Continuously polls the presenter for data, formats it, and broadcasts
        to all connected clients. Runs until stop() is called.
        """
        logger.info("Broadcast loop started")

        while self._running:
            try:
                streams_data = self.presenter.poll_data()

                if streams_data:
                    frame = self.format_frame(streams_data)
                    self._broadcast_to_clients(frame)

                time.sleep(self.broadcast_interval)

            except Exception as err:
                logger.error("Error in broadcast loop: %s", err)
                time.sleep(self.broadcast_interval)

        logger.info("Broadcast loop ended")

    def _broadcast_to_clients(self, message: str) -> None:
        """Sends a message to all connected clients.

        Iterates through all clients and sends the message asynchronously.
        Disconnected clients are removed from the set.

        Args:
            message: The JSON message string to broadcast.
        """
        with self._clients_lock:
            clients_snapshot = set(self.clients)

        disconnected: List[server.ServerConnection] = []

        for client in clients_snapshot:
            try:
                if self._loop is not None:
                    future = asyncio.run_coroutine_threadsafe(
                        client.send(message), self._loop
                    )
                    future.result(timeout=self.CLIENT_SEND_TIMEOUT)
            except Exception as err:
                logger.warning("Failed to send to client: %s", err)
                disconnected.append(client)

        for client in disconnected:
            self.remove_client(client)
