"""Main entry point for MoBI-View application.

Discovers LSL streams, creates DataInlets and MainAppPresenter, then starts
the WebSocket server with browser interface.
"""

import logging
import threading
import webbrowser

from MoBI_View.core.discovery import discover_and_create_inlets
from MoBI_View.presenters.main_app_presenter import MainAppPresenter


def schedule_browser_launch() -> None:
    """Opens browser to application URL after short delay."""

    def _launch() -> None:
        # Default host and port - will be configurable in future branch
        host = "localhost"
        port = 8765
        url = f"http://{host}:{port}"
        try:
            webbrowser.open(url, new=2, autoraise=True)
        except webbrowser.Error as exc:  # pragma: no cover
            logging.getLogger(__name__).warning("Browser launch failed: %s", exc)

    timer = threading.Timer(0.5, _launch)
    timer.daemon = True
    timer.start()


def main() -> None:
    """Discovers LSL streams and creates presenter (web server in future branch)."""
    print("Discovering LSL streams...")

    inlets, count = discover_and_create_inlets(wait_time=1.0)

    if count == 0:
        print("No LSL streams found.")
        print("Future: Use 'Discover Streams' button in web UI to search for streams.")
    else:
        print(f"Found {count} stream(s)")

    presenter = MainAppPresenter(data_inlets=inlets)
    print(f"Created presenter with {len(presenter.data_inlets)} inlet(s)")
    print("Note: Web server functionality will be added in future branch")


if __name__ == "__main__":
    main()
