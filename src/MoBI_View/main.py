"""Module providing the main entry point for the MoBI_View application.

This module discovers all available LSL streams, creates DataInlet objects for each,
and initializes the MainAppPresenter and MainAppView. It then launches the PyQt6
application event loop.

Usage:
    python -m src.MoBI_View.main
"""

import sys
from typing import List

from pylsl import resolve_streams
from PyQt6.QtWidgets import QApplication

from MoBI_View.core.data_inlet import DataInlet
from MoBI_View.presenters.main_app_presenter import MainAppPresenter
from MoBI_View.views.main_app_view import MainAppView


def main() -> None:
    """Launches the MoBI_View application."""
    app = QApplication(sys.argv)
    print("Resolving LSL streams...")

    discovered_streams = resolve_streams()
    data_inlets: List[DataInlet] = []
    stream_info_map: dict[str, str] = {}

    for info in discovered_streams:
        try:
            inlet = DataInlet(info)
            data_inlets.append(inlet)
            stream_info_map[inlet.stream_name] = inlet.stream_type
            print(
                f"Discovered stream: Name={inlet.stream_name}, Type={inlet.stream_type}"
            )
        except Exception as err:
            print(f"Skipping stream {info.name()} due to: {err}")

    main_view = MainAppView(stream_info=stream_info_map)
    _presenter = MainAppPresenter(view=main_view, data_inlets=data_inlets)

    main_view.show()

    print("Starting application event loop...")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
