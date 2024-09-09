"""This module provides utility functions for the GUI."""


import pyqtgraph as pg
from data_inlet import DataInlet
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QVBoxLayout


def setup_plot_widget(layout: QVBoxLayout) -> pg.PlotWidget:
    """Create and set up plot widgets."""
    plot_widget = pg.PlotWidget(title="Multi-Channel LSL Plot (Excluding First)")
    layout.addWidget(plot_widget)
    return plot_widget

def start_data_timer(inlet: DataInlet) -> None:
    """Start the timer to pull and plot data."""
    timer = QTimer()
    timer.timeout.connect(inlet.pull_and_plot)
    timer.start(50)  # Update every 50ms
