"""This module is the main entry point for the MoBI GUI application."""

import sys

import pylsl
from pyqtgraph.Qt import QtWidgets
from window import MainAppWindow


def main() -> None:
    """Main function for the MoBI GUI application."""
    streams = pylsl.resolve_streams()  # Resolving all streams
    if not streams:
        print("No streams found.")
        return

    app = QtWidgets.QApplication(sys.argv)
    main_window = MainAppWindow(streams)
    main_window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
