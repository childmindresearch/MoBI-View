"""Main entry point for MoBI-View application.

Discovers LSL streams, creates DataInlets and MainAppPresenter, then starts
the WebSocket server with browser interface.
"""

import logging
import threading
import webbrowser

from MoBI_View.core import discovery
from MoBI_View.presenters import main_app_presenter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger("MoBI-View.main")


def schedule_browser_launch() -> None:
    """Opens browser to application URL after short delay."""

    def _launch() -> None:
        host = "localhost"
        port = 8765
        url = f"http://{host}:{port}"
        try:
            webbrowser.open(url, new=2, autoraise=True)
        except webbrowser.Error as exc:  # pragma: no cover
            logger.warning("Browser launch failed: %s", exc)

    timer = threading.Timer(0.5, _launch)
    timer.daemon = True
    timer.start()


def main() -> None:
    """Discovers LSL streams and creates presenter (web server in future branch)."""
    logger.info("Discovering LSL streams...")

    inlets = discovery.discover_and_create_inlets()

    if not inlets:
        logger.info("No LSL streams found.")
        logger.info(
            "Future: Use 'Discover Streams' button in web UI to search for streams."
        )
    else:
        logger.info("Found %d stream(s)", len(inlets))

    presenter = main_app_presenter.MainAppPresenter(data_inlets=inlets)
    logger.info("Created presenter with %d inlet(s)", len(presenter.data_inlets))
    logger.info("Note: Web server functionality will be added in future branch")


if __name__ == "__main__":
    main()
