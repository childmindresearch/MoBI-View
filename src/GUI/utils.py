"""This module provides utility functions for the GUI."""

from typing import Any, Callable, Tuple

import pyqtgraph as pg
from PyQt5.QtCore import QTimer
from pyqtgraph import PlotWidget


def setup_plot_widget(layout: Callable[[], None]) -> Tuple[PlotWidget, Any]:
    """Create and set up plot widgets."""
    plot_widget = pg.PlotWidget(title="Multi-Channel LSL Plot")
    layout.addWidget(plot_widget)
    return plot_widget, layout


def start_data_timer(inlet: Callable[[], None]) -> None:
    """Start the timer to pull and plot data."""
    timer = QTimer()
    timer.timeout.connect(inlet.pull_and_plot)
    timer.start(50)  # Update every 50ms
