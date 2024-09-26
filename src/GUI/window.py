"""Module for handling GUI components of the MoBI application."""
import math

import pylsl
import pyqtgraph as pg
from config import TIMER_INTERVAL
from data_inlet import DataInlet
from pyqtgraph.Qt import QtCore, QtWidgets


class MainAppWindow(QtWidgets.QMainWindow):
    """Main application window that holds multiple plot windows with control panel."""

    def __init__(self, streams: list) -> None:
        """Initialize the main application window with the given streams."""
        super().__init__()

        self.setWindowTitle("MoBI GUI Application - Stream Viewer")
        self.setGeometry(100, 100, 1600, 900)  # Adjusted width for better layout

        # Central widget with horizontal layout
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QtWidgets.QHBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(10)

        # Control Panel on the left
        control_panel = QtWidgets.QWidget()
        control_layout = QtWidgets.QVBoxLayout(control_panel)
        control_layout.setAlignment(QtCore.Qt.AlignTop)
        control_layout.setContentsMargins(10, 10, 10, 10)
        control_layout.setSpacing(10)

        control_label = QtWidgets.QLabel("Control Panel")
        control_label.setStyleSheet("font-weight: bold; font-size: 16px;")
        control_layout.addWidget(control_label)

        # Use QTreeWidget for hierarchical stream and channel checkboxes
        tree_widget = QtWidgets.QTreeWidget()
        tree_widget.setHeaderHidden(True)
        tree_widget.setMaximumWidth(250)
        tree_widget.setStyleSheet("QTreeWidget::item { padding: 5px; }")

        # Dictionary to hold references to DataInlet instances and plot widgets
        self.inlets = []
        self.plot_widgets = {}
        self.tree_items = {}

        # Block signals while setting up the tree to prevent unwanted handler invocations
        tree_widget.blockSignals(True)

        for stream in streams:
            stream_name = stream.name()
            source_id = stream.source_id()

            # Create a PlotWidget for the stream
            plot_widget = pg.PlotWidget(title=f"{stream_name} Stream")
            plot_widget.setBackground('w')  # White background for better visibility
            plot_widget.showGrid(x=True, y=True, alpha=0.3)
            plot_widget.setLabel('left', 'Amplitude')
            plot_widget.setLabel('bottom', 'Time', units='s')
            plot_widget.enableAutoRange('y', True)
            plot_widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
            self.plot_widgets[source_id] = plot_widget

            # Retrieve the PlotItem from the PlotWidget
            plot_item = plot_widget.getPlotItem()

            # Create a top-level tree item for the stream
            stream_item = QtWidgets.QTreeWidgetItem(tree_widget)
            stream_item.setText(0, f"{stream_name}")
            stream_item.setCheckState(0, QtCore.Qt.Checked)
            self.tree_items[source_id] = stream_item

            # Make the stream item checkable
            stream_item.setFlags(stream_item.flags() | QtCore.Qt.ItemIsUserCheckable)

            # Create DataInlet and associated channels
            inlet = DataInlet(stream, plot_item)
            self.inlets.append(inlet)

            for channel_name in inlet.channel_names:
                channel_item = QtWidgets.QTreeWidgetItem(stream_item)
                channel_item.setText(0, channel_name)
                channel_item.setCheckState(0, QtCore.Qt.Checked)
                channel_item.setFlags(channel_item.flags() | QtCore.Qt.ItemIsUserCheckable)

        # Unblock signals after setting up the tree
        tree_widget.blockSignals(False)

        # Expand all tree items by default
        tree_widget.expandAll()

        # Connect a single handler for all itemChanged events
        tree_widget.itemChanged.connect(self.handle_item_changed)

        # Add the tree widget to the control layout
        control_layout.addWidget(tree_widget)

        # Add stretch to push the widgets to the top
        control_layout.addStretch()

        # Add control panel to the main layout
        main_layout.addWidget(control_panel)

        # Create a widget for plots with a grid layout
        plots_container = QtWidgets.QWidget()
        grid_layout = QtWidgets.QGridLayout(plots_container)
        grid_layout.setAlignment(QtCore.Qt.AlignTop)
        grid_layout.setSpacing(10)

        # Determine grid size based on number of streams (up to 6)
        num_streams = len(streams)
        num_columns = 3  # For up to 6 streams, 2 rows x 3 columns
        num_rows = math.ceil(num_streams / num_columns)

        for idx, (source_id, plot_widget) in enumerate(self.plot_widgets.items()):
            row = idx // num_columns
            col = idx % num_columns
            grid_layout.addWidget(plot_widget, row, col)

        # Add plots container to main layout
        main_layout.addWidget(plots_container, 4)

        # Timer for updating plots
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_all_inlets)
        self.timer.start(TIMER_INTERVAL)

    def handle_item_changed(self, item: QtWidgets.QTreeWidgetItem, column: int) -> None:
        """Handle the state change of a stream's or channel's checkbox.

        Args:
            item (QTreeWidgetItem): The tree item that was changed.
            column (int): The column of the item.
        """
        # Check if the item is a top-level stream item
        if item.parent() is None:
            # Stream checkbox changed
            stream_name = item.text(0)
            source_id = None
            # Find the corresponding source_id
            for sid, s_item in self.tree_items.items():
                if s_item == item:
                    source_id = sid
                    break
            if source_id:
                state = item.checkState(0)
                plot_widget = self.plot_widgets.get(source_id)
                if plot_widget:
                    plot_widget.setVisible(state == QtCore.Qt.Checked)
        else:
            # Channel checkbox changed
            channel_name = item.text(0)
            parent_item = item.parent()
            # Find the source_id from the parent_item
            source_id = None
            for sid, s_item in self.tree_items.items():
                if s_item == parent_item:
                    source_id = sid
                    break
            if source_id:
                state = item.checkState(0)
                # Find the corresponding DataInlet
                for inlet in self.inlets:
                    if inlet.inlet.info().source_id() == source_id:
                        inlet.toggle_channel_visibility(channel_name, state == QtCore.Qt.Checked)
                        break

    def update_all_inlets(self) -> None:
        """Update all inlets by pulling and plotting new data."""
        for inlet in self.inlets:
            source_id = inlet.inlet.info().source_id()
            plot_widget = self.plot_widgets.get(source_id)
            if plot_widget and plot_widget.isVisible():
                inlet.pull_and_plot()
