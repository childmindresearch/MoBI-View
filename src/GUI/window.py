"""Module for handling GUI components of the MoBI application."""

import pylsl
import pyqtgraph as pg
from config import TIMER_INTERVAL
from data_inlet import DataInlet
from pyqtgraph.Qt import QtCore, QtWidgets


class MainAppWindow(QtWidgets.QMainWindow):
    """Main application window that holds multiple dockable stream windows."""

    def __init__(self, streams: list) -> None:
        """Initialize the main application window with the given streams."""
        super().__init__()

        self.setWindowTitle("MoBI GUI Application - Stream Viewer")
        self.setGeometry(100, 100, 1200, 800)

        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)

        self.docks = []
        self.inlets = []

        for stream in streams:
            dock = QtWidgets.QDockWidget(f"Stream: {stream.name()}", self)
            dock.setAllowedAreas(QtCore.Qt.AllDockWidgetAreas)

            stream_widget = QtWidgets.QWidget()
            layout = QtWidgets.QVBoxLayout(stream_widget)

            plot_widget = pg.PlotWidget(title=f"Multi-Channel LSL Plot - {stream.name()}")
            layout.addWidget(plot_widget)

            inlet = DataInlet(stream, plot_widget.getPlotItem(), layout)
            self.inlets.append(inlet)

            stream_widget.setLayout(layout)
            dock.setWidget(stream_widget)
            self.addDockWidget(QtCore.Qt.RightDockWidgetArea, dock)

            self.docks.append(dock)

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_all_inlets)
        self.timer.start(TIMER_INTERVAL)

    def update_all_inlets(self) -> None:
        for inlet in self.inlets:
            inlet.pull_and_plot()