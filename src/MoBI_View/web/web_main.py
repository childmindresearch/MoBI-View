"""Minimal entry point for running MoBI-View in web mode.

The command ``mobi-view-web`` starts the WebSocket server and static file host
with minimal dependencies using defaults from :mod:`MoBI_View.core.config`.
"""

from __future__ import annotations

import logging
import threading
import webbrowser

from MoBI_View.core.config import Config
from MoBI_View.web.server import run_web


def main() -> None:
    """Run the MoBI-View minimal web UI and WebSocket server."""
    schedule_browser_launch()
    run_web()


def schedule_browser_launch() -> None:
    """Open the default browser to the HTTP endpoint after a short delay."""

    def _launch() -> None:
        host = Config.HTTP_HOST
        if host in {"0.0.0.0", "::"}:
            host_display = "localhost"
        else:
            host_display = host
        port = Config.HTTP_PORT
        url = f"http://{host_display}:{port}"
        try:
            webbrowser.open(url, new=2, autoraise=True)
        except webbrowser.Error as exc:  # pragma: no cover
            logging.getLogger(__name__).warning("Browser launch failed: %s", exc)

    timer = threading.Timer(0.5, _launch)
    timer.daemon = True
    timer.start()
