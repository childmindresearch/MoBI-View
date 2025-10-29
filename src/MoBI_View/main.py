"""Main entry point for MoBI-View application.

Discovers LSL streams, creates DataInlets and MainAppPresenter, then starts
the WebSocket server with browser interface.
"""

import asyncio
import logging
import threading
import webbrowser

from MoBI_View.core.config import Config
from MoBI_View.core.discovery import discover_and_create_inlets
from MoBI_View.presenters.main_app_presenter import MainAppPresenter
from MoBI_View.web.server import run_server


def schedule_browser_launch() -> None:
    """Opens browser to application URL after short delay."""

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


def main() -> None:
    """Discovers LSL streams and starts web server with browser interface."""
    print("Discovering LSL streams...")

    inlets, count = discover_and_create_inlets(wait_time=1.0)

    if count == 0:
        print("No LSL streams found. Server will start with empty stream list.")
        print("Use the 'Discover Streams' button in the web UI to search for streams.")
    else:
        print(f"Found {count} stream(s)")

    presenter = MainAppPresenter(data_inlets=inlets)

    schedule_browser_launch()
    asyncio.run(run_server(presenter))


if __name__ == "__main__":
    main()
