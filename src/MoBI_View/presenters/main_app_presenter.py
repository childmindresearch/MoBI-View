"""Module providing the MainAppPresenter class for MoBI_View."""

from typing import Dict, List

import numpy as np
from PyQt6.QtCore import QTimer

from MoBI_View.core import config, data_inlet, exceptions
from MoBI_View.views import interfaces


class MainAppPresenter:
    """Presenter handling interactions between DataInlet (Model) and MainAppView (View).

    This class processes data from DataInlet instances and updates the View accordingly.
    It also manages user interactions related to channel visibility.

    Attributes:
        view: An instance of a view class implementing IMainAppView.
        data_inlets: A list of DataInlet instances for data acquisition.
        channel_visibility: A dictionary tracking the visibility of each channel.
        timer: A QTimer instance for polling data at regular intervals.
        channel_labels: List of labels for each channel in the sample.
    """

    def __init__(
        self,
        view: interfaces.IMainAppView,
        data_inlets: List[data_inlet.DataInlet],
    ) -> None:
        """Initializes the MainAppPresenter with the given view and data inlets.

        Args:
            view: An instance of a view class implementing IMainAppView.
            data_inlets: A list of DataInlet instances for data acquisition.
        """
        self.view: interfaces.IMainAppView = view
        self.data_inlets: List[data_inlet.DataInlet] = data_inlets
        self.channel_visibility: Dict[str, bool] = {}

        self.timer: QTimer = QTimer()
        self.timer.setInterval(config.Config.TIMER_INTERVAL)
        self.timer.timeout.connect(self.poll_data)
        self.timer.start()

        self._initialize_channels()

    def _initialize_channels(self) -> None:
        """Initializes channel visibility and registers toggle callbacks."""
        for inlet in self.data_inlets:
            for channel_label in inlet.channel_info["labels"]:
                channel_name = f"{inlet.stream_name}:{channel_label}"
                self.channel_visibility[channel_name] = True
                self.view.set_plot_channel_visibility(channel_name, True)
                self.view.add_tree_item(inlet.stream_name, channel_name)

    def poll_data(self) -> None:
        """Polls each DataInlet for new data and updates the View accordingly.

        Raises:
            StreamLostError: If connection to a data stream is lost or interrupted.
            InvalidChannelCountError: If the received data has an unexpected number
                of channels.
            InvalidChannelFormatError: If the data format from the stream doesn't
                match the expected format.
            Exception: For any other unexpected errors during data polling.
        """
        for inlet in self.data_inlets:
            try:
                inlet.pull_sample()
                if inlet.ptr == 0:
                    continue
                latest_index = (inlet.ptr - 1) % config.Config.BUFFER_SIZE
                sample = inlet.buffers[latest_index]
                channel_labels = inlet.channel_info["labels"]
                self.on_data_updated(inlet.stream_name, sample, channel_labels)
            except exceptions.StreamLostError as e:
                self.view.display_error(str(e))
            except exceptions.InvalidChannelCountError as e:
                self.view.display_error(str(e))
            except exceptions.InvalidChannelFormatError as e:
                self.view.display_error(str(e))
            except Exception as e:
                self.view.display_error(f"Unexpected error: {str(e)}")

    def on_data_updated(
        self, stream_name: str, sample: np.ndarray, channel_labels: List[str]
    ) -> None:
        """Handles data updates from DataInlet instances and updates the View.

        Args:
            stream_name: Identifier for the data source.
            sample: The new data sample as a NumPy array.
            channel_labels: List of labels for each channel in the sample.
        """
        plot_data = {
            "stream_name": stream_name,
            "data": sample.tolist(),
            "channel_labels": channel_labels,
        }
        self.view.update_plot(plot_data)

    def update_channel_visibility(self, channel_name: str, visible: bool) -> None:
        """Updates the visibility of a specific data channel.

        Args:
            channel_name: The unique name of the channel to toggle.
            visible: True to show the channel, False to hide it.
        """
        self.channel_visibility[channel_name] = visible
        self.view.set_plot_channel_visibility(channel_name, visible)
