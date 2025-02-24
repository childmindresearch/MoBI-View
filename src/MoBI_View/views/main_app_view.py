"""Module providing the MainAppView class for MoBI_View.

Implements the main application window, which orchestrates an EEG tab
(EEGPlotWidget), a numeric-data tab (MultiStreamNumericContainer), and a
QTreeWidget-based control panel for toggling channel visibility. Also adds a
reset button in the status bar to restore the control panel.
"""

from typing import Dict, cast

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDockWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStatusBar,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from MoBI_View.views.eeg_plot_widget import EEGPlotWidget
from MoBI_View.views.numeric_plot_widget import MultiStreamNumericContainer


class MainAppView(QMainWindow):
    """Main application window for MoBI_View.

    Attributes:
        _channel_visibility: Maps "Stream:Channel" to bool indicating visibility.
        _stream_channels: Maps stream names to a set of channel names.
        _stream_types: Maps stream names to a string describing the stream type.
        _tab_widget: QTabWidget containing the EEG and numeric-data tabs.
        _eeg_tab: EEGPlotWidget for displaying EEG data.
        _non_eeg_tab: MultiStreamNumericContainer for displaying numeric data.
        _stream_items: Maps stream names to QTreeWidgetItem for top-level nodes.
        _channel_items: Maps "Stream:Channel" to QTreeWidgetItem for child nodes.
        _dock: QDockWidget for the control panel.
        _tree_widget: QTreeWidget for displaying stream and channel controls.
    """

    def __init__(
        self, stream_info: Dict[str, str], parent: QWidget | None = None
    ) -> None:
        """Initializes the main view window.

        Args:
            stream_info: Maps stream names to stream types.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self.setWindowTitle("MoBI_View")
        self._channel_visibility: Dict[str, bool] = {}
        self._stream_channels: Dict[str, set[str]] = {}
        self._stream_types: Dict[str, str] = stream_info

        self._init_ui()
        self.show()

    def _init_ui(self) -> None:
        """Initializes the user interface for the main window."""
        self._init_central_widget()
        self._init_dock_widget()
        self._init_status_bar()

    def _init_central_widget(self) -> None:
        """Sets up the central widget and tab areas."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout()
        central_widget.setLayout(layout)

        self._tab_widget = QTabWidget()
        layout.addWidget(self._tab_widget)

        self._eeg_tab = EEGPlotWidget()
        self._tab_widget.addTab(self._eeg_tab, "EEG Data")

        self._non_eeg_tab = MultiStreamNumericContainer()
        self._tab_widget.addTab(self._non_eeg_tab, "Numeric Data")

    def _init_dock_widget(self) -> None:
        """Sets up the dock widget and tree control."""
        self._stream_items: Dict[str, QTreeWidgetItem] = {}
        self._channel_items: Dict[str, QTreeWidgetItem] = {}

        self._dock = QDockWidget("Control Panel", self)
        self._dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea
        )
        self._dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetClosable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
            | QDockWidget.DockWidgetFeature.DockWidgetMovable
        )
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self._dock)

        self._tree_widget = QTreeWidget()
        self._tree_widget.setHeaderLabel("Streams / Channels")
        self._dock.setWidget(self._tree_widget)
        self._tree_widget.itemChanged.connect(self._on_tree_item_changed)

    def _init_status_bar(self) -> None:
        """Configures the status bar with a message and a reset button."""
        self.setStatusBar(QStatusBar(self))
        status_bar = cast(QStatusBar, self.statusBar())
        status_bar.showMessage("Status: OK")
        reset_button = QPushButton("Reset Control Panel")
        reset_button.clicked.connect(self.reset_control_panel)
        status_bar.addPermanentWidget(reset_button)

    def reset_control_panel(self) -> None:
        """Resets and shows the control panel dock widget."""
        self._dock.show()

    def add_tree_item(self, stream_name: str, channel_name: str) -> None:
        """Adds QTreeWidgetItems for a given stream and channel.

        Args:
            stream_name: Name of the LSL stream.
            channel_name: Full channel identifier (e.g. "EEGStream:Fz").
        """
        if stream_name not in self._stream_items:
            stream_item = QTreeWidgetItem(self._tree_widget)
            stream_item.setText(0, stream_name)
            flags = stream_item.flags() | Qt.ItemFlag.ItemIsUserCheckable
            stream_item.setFlags(flags)
            stream_item.setCheckState(0, Qt.CheckState.Checked)
            self._stream_items[stream_name] = stream_item
            self._stream_channels[stream_name] = set()

        if channel_name not in self._channel_items:
            parent_item = self._stream_items[stream_name]
            channel_item = QTreeWidgetItem(parent_item)
            channel_item.setText(0, channel_name.split(":", 1)[-1])
            flags = channel_item.flags() | Qt.ItemFlag.ItemIsUserCheckable
            channel_item.setFlags(flags)
            channel_item.setCheckState(0, Qt.CheckState.Checked)
            self._channel_items[channel_name] = channel_item

    def update_plot(self, data: dict) -> None:
        """Updates the plots with new data from a stream.

        Args:
            data: A dict with keys "stream_name", "data", and "channel_labels".
        """
        stream_name = data.get("stream_name", "")
        sample_list = data.get("data", [])
        channel_labels = data.get("channel_labels", [])
        for i, val in enumerate(sample_list):
            label = channel_labels[i] if i < len(channel_labels) else f"Channel{i+1}"
            chan_name = f"{stream_name}:{label}"
            visible = self._channel_visibility[chan_name]
            if self._stream_types.get(stream_name) == "EEG":
                self._eeg_tab.update_data(chan_name, val, visible)
            else:
                self._non_eeg_tab.update_data(stream_name, chan_name, val, visible)

    def set_plot_channel_visibility(self, channel_name: str, visible: bool) -> None:
        """Toggles the visibility of a channel.

        Args:
            channel_name: Full channel identifier.
            visible: True to show the channel, False to hide it.
        """
        self._channel_visibility[channel_name] = visible

    def display_error(self, message: str) -> None:
        """Displays an error message via a dialog and updates the status bar.

        Args:
            message: The error message to display.
        """
        QMessageBox.critical(self, "Error", message)
        status_bar = cast(QStatusBar, self.statusBar())
        status_bar.showMessage(f"Status: {message}")

    def _on_tree_item_changed(self, item: QTreeWidgetItem) -> None:
        """Handles changes in the control panel tree to update channel visibility.

        Args:
            item: The QTreeWidgetItem that changed.
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
            is_visible = item.checkState(0) == Qt.CheckState.Checked
            self.set_plot_channel_visibility(full_name, is_visible)
