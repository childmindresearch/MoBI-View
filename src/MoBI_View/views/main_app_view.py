"""Module providing the MainAppView class for MoBI_View.

Implements the main application window, which orchestrates an
EEG tab (eeg_plot_widget.EEGPlotWidget), a numeric-data tab
(numeric_plot_widget.MultiStreamNumericContainer), and a QtWidgets.QTreeWidget-based
control panel for toggling channel visibility. Also adds a reset button in the status
bar to restore the control panel.
"""

from typing import Dict, cast

from PyQt6 import QtCore, QtWidgets

from MoBI_View.views import eeg_plot_widget, numeric_plot_widget


class MainAppView(QtWidgets.QMainWindow):
    """Main application window for MoBI_View.

    This window manages tabs for different data visualizations (EEG and numeric-data),
    provides a tree-based control panel for toggling channel visibility, and maintains
    the mapping between data streams and their visual representations.

    Attributes:
        _channel_visibility: Maps "Stream:Channel" to bool indicating visibility.
        _stream_types: Maps stream names to a string describing the stream type.
        _tab_widget: QtWidgets.QTabWidget containing the EEG and numeric-data tabs.
        _eeg_tab: eeg_plot_widget.EEGPlotWidget for displaying EEG data.
        _numeric_tab: numeric_plot_widget.MultiStreamNumericContainer for displaying
            non-EEG numeric data.
        _stream_items: Maps stream names to QtWidgets.QTreeWidgetItem for top-level
            nodes.
        _channel_items: Maps "Stream:Channel" to QtWidgets.QTreeWidgetItem for child
            nodes.
        _dock: QtWidgets.QDockWidget for the control panel.
        _tree_widget: QtWidgets.QTreeWidget for displaying stream and channel controls.
    """

    def __init__(
        self, stream_info: Dict[str, str], parent: QtWidgets.QWidget | None = None
    ) -> None:
        """Initializes the main view window with UI components and data structures.

        Args:
            stream_info: Maps stream names to stream types (e.g., {"EEGStream": "EEG"}).
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self.setWindowTitle("MoBI_View")
        self._channel_visibility: Dict[str, bool] = {}
        self._stream_types: Dict[str, str] = stream_info

        self._init_ui()
        self.show()

    def _init_ui(self) -> None:
        """Initializes the user interface for the main window."""
        self._init_central_widget()
        self._init_dock_widget()
        self._init_status_bar()

    def _init_central_widget(self) -> None:
        """Sets up the central widget containing tab areas for different visualizations.

        Creates a tab widget with separate tabs for EEG and numeric data, each
        containing specialized visualization widgets.
        """
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        layout = QtWidgets.QVBoxLayout()
        central_widget.setLayout(layout)

        self._tab_widget = QtWidgets.QTabWidget()
        layout.addWidget(self._tab_widget)

        self._eeg_tab = eeg_plot_widget.EEGPlotWidget()
        self._tab_widget.addTab(self._eeg_tab, "EEG Data")

        self._numeric_tab = numeric_plot_widget.MultiStreamNumericContainer()
        self._tab_widget.addTab(self._numeric_tab, "Numeric Data")

    def _init_dock_widget(self) -> None:
        """Sets up dock widget and tree control for channel visibility management."""
        self._stream_items: Dict[str, QtWidgets.QTreeWidgetItem] = {}
        self._channel_items: Dict[str, QtWidgets.QTreeWidgetItem] = {}

        self._create_dock_widget()
        self._create_tree_widget()

    def _create_dock_widget(self) -> None:
        """Creates and configures the dockable control panel."""
        self._dock = QtWidgets.QDockWidget("Control Panel", self)
        self._dock.setAllowedAreas(
            QtCore.Qt.DockWidgetArea.LeftDockWidgetArea
            | QtCore.Qt.DockWidgetArea.RightDockWidgetArea
        )
        self._dock.setFeatures(
            QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetClosable
            | QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetFloatable
            | QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetMovable
        )
        self.addDockWidget(QtCore.Qt.DockWidgetArea.LeftDockWidgetArea, self._dock)

    def _create_tree_widget(self) -> None:
        """Creates and configures the tree widget for stream and channel control."""
        self._tree_widget = QtWidgets.QTreeWidget()
        self._tree_widget.setHeaderLabel("Streams / Channels")
        self._dock.setWidget(self._tree_widget)
        self._tree_widget.itemChanged.connect(self._on_tree_item_changed)

    def _init_status_bar(self) -> None:
        """Configures the status bar with a message and a control panel reset button.

        Adds a permanent widget (reset button) to the right side of the status bar
        that allows users to restore the control panel if it has been closed or hidden.
        """
        self.setStatusBar(QtWidgets.QStatusBar(self))
        status_bar = cast(QtWidgets.QStatusBar, self.statusBar())
        status_bar.showMessage("Status: OK")
        reset_button = QtWidgets.QPushButton("Reset Control Panel")
        reset_button.clicked.connect(self._dock.show)
        status_bar.addPermanentWidget(reset_button)

    def add_tree_item(self, stream_name: str, channel_name: str) -> None:
        """Adds hierarchical items to the control panel tree for visibility control.

        This method manages the creation and organization of items in the tree widget
        that controls channel visibility. It ensures each stream appears only once as
        a top-level item, and each channel appears as a child of its parent stream.

        When a new stream is encountered, this method creates a checkable tree item
        for it and initializes tracking structures. When a new channel is encountered,
        it creates a child item under the appropriate stream with the display name
        extracted from the full channel identifier. (Lazy initialization)

        All items are initially created in the checked (visible) state and are made
        user-checkable to allow toggling visibility through the control panel.

        Args:
            stream_name: Name of the LSL stream (e.g., "EEGStream").
            channel_name: Fully qualified identifier including stream prefix
                (e.g., "EEGStream:Fz").
        """
        if stream_name not in self._stream_items:
            stream_item = QtWidgets.QTreeWidgetItem(self._tree_widget)
            stream_item.setText(0, stream_name)
            flags = stream_item.flags() | QtCore.Qt.ItemFlag.ItemIsUserCheckable
            stream_item.setFlags(flags)
            stream_item.setCheckState(0, QtCore.Qt.CheckState.Checked)
            self._stream_items[stream_name] = stream_item

        if channel_name not in self._channel_items:
            parent_item = self._stream_items[stream_name]
            channel_item = QtWidgets.QTreeWidgetItem(parent_item)
            channel_item.setText(0, channel_name.split(":", 1)[-1])
            flags = channel_item.flags() | QtCore.Qt.ItemFlag.ItemIsUserCheckable
            channel_item.setFlags(flags)
            channel_item.setCheckState(0, QtCore.Qt.CheckState.Checked)
            self._channel_items[channel_name] = channel_item

    def update_plot(self, data: dict) -> None:
        """Updates the plots with new data from a stream.

        Routes incoming data samples to the appropriate visualization tab based on
        the stream type. EEG data is sent to the EEG tab, while all other data types
        are sent to the numeric data tab.

        Args:
            data: A dictionary containing stream data with keys:
                "stream_name": Name of the data stream.
                "data": List of sample values.
                "channel_labels": List of channel names corresponding to samples
                    (not fully qualified).
        """
        stream_name = data.get("stream_name", "")
        sample_list = data.get("data", [])
        channel_labels = data.get("channel_labels", [])
        for idx, val in enumerate(sample_list):
            label = (
                channel_labels[idx]
                if idx < len(channel_labels)
                else f"Channel{idx + 1}"
            )
            chan_name = f"{stream_name}:{label}"
            visible = self._channel_visibility[chan_name]
            if self._stream_types.get(stream_name) == "EEG":
                self._eeg_tab.update_data(chan_name, val, visible)
            else:
                self._numeric_tab.update_numeric_containers(
                    stream_name, chan_name, val, visible
                )

    def set_plot_channel_visibility(self, channel_name: str, visible: bool) -> None:
        """Toggles the visibility of a channel.

        Args:
            channel_name: Fully qualified channel identifier (e.g., "EEGStream:Fz").
            visible: True to show the channel, False to hide it.
        """
        self._channel_visibility[channel_name] = visible

    def display_error(self, message: str) -> None:
        """Displays an error message via a dialog and updates the status bar.

        Args:
            message: The error message to display.
        """
        QtWidgets.QMessageBox.critical(self, "Error", message)
        status_bar = cast(QtWidgets.QStatusBar, self.statusBar())
        status_bar.showMessage(f"Status: {message}")

    def _on_tree_item_changed(self, item: QtWidgets.QTreeWidgetItem) -> None:
        """Handles changes in the control panel tree to update channel visibility.

        When a top-level (stream) item is clicked, this method applies the same
        visibility state to all child (channel) items. When a child item is
        clicked, it updates only that specific channel's visibility.

        Args:
            item: The tree widget item that was changed.
        """
        parent_item = item.parent()
        if parent_item is None:
            new_state = item.checkState(0)
            for i in range(item.childCount()):
                child = item.child(i)
                if child is not None:
                    child.setCheckState(0, new_state)
        else:
            short_name = item.text(0)
            stream_name = parent_item.text(0)
            full_name = f"{stream_name}:{short_name}"
            is_visible = item.checkState(0) == QtCore.Qt.CheckState.Checked
            self.set_plot_channel_visibility(full_name, is_visible)
