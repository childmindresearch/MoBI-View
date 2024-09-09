"""This module is the main entry point for the MoBI GUI application."""

import sys

import pylsl
from data_inlet import DataInlet
from PyQt5.QtWidgets import QApplication, QVBoxLayout, QWidget
from utils import setup_plot_widget, start_data_timer


def main() -> None:
    """Main function for the MoBI GUI application."""
    # Resolve the LSL stream
    streams = pylsl.resolve_stream('type', 'Gaze')  # Assuming Gaze stream
    if not streams:
        print("No streams found.")
        return

    # Create the application instance
    app = QApplication(sys.argv)
    win = QWidget()
    layout = QVBoxLayout(win)

    # Create and set up the plot and text widgets
    plot_widget, layout = setup_plot_widget(layout)
    
    # Create the DataInlet instance
    inlet = DataInlet(streams[0], plot_widget.getPlotItem(), layout)

    # Start the timer for data updating
    start_data_timer(inlet)

    # Show the main window
    win.setLayout(layout)
    win.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
