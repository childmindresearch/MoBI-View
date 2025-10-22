"""Module providing the MainAppPresenter class for MoBI_View."""

from typing import Any, Dict, List

import numpy as np

from MoBI_View.core import config, data_inlet, exceptions


class MainAppPresenter:
    """Presenter managing data inlets and channel visibility.

    This class processes data from DataInlet instances, manages channel state,
    and provides data for consumption by external systems (e.g., web servers).

    Attributes:
        data_inlets: A list of DataInlet instances for data acquisition.
        channel_visibility: A dictionary tracking the visibility of each channel.
    """

    def __init__(
        self,
        data_inlets: List[data_inlet.DataInlet],
    ) -> None:
        """Initializes the MainAppPresenter with the given data inlets.

        Args:
            data_inlets: A list of DataInlet instances for data acquisition.
        """
        self.data_inlets: List[data_inlet.DataInlet] = data_inlets
        self.channel_visibility: Dict[str, bool] = {}

        self._initialize_channels()

    def _initialize_channels(self) -> None:
        """Initializes channel visibility for all discovered channels."""
        for inlet in self.data_inlets:
            for channel_label in inlet.channel_info["labels"]:
                channel_name = f"{inlet.stream_name}:{channel_label}"
                self.channel_visibility[channel_name] = True

    def poll_data(self) -> List[Dict[str, Any]]:
        """Polls each DataInlet for new data and returns plot data.

        Returns:
            List of plot data dictionaries, one per inlet that has new samples.
            Each dictionary contains 'stream_name', 'data', and 'channel_labels'.

        Raises:
            StreamLostError: If connection to a data stream is lost or interrupted.
            InvalidChannelCountError: If the received data has an unexpected number
                of channels.
            InvalidChannelFormatError: If the data format from the stream doesn't
                match the expected format.
            Exception: For any other unexpected errors during data polling.
        """
        results = []
        for inlet in self.data_inlets:
            try:
                inlet.pull_sample()
                if inlet.ptr == 0:
                    continue
                latest_index = (inlet.ptr - 1) % config.Config.BUFFER_SIZE
                sample = inlet.buffers[latest_index]
                channel_labels = inlet.channel_info["labels"]
                plot_data = self.on_data_updated(
                    inlet.stream_name, sample, channel_labels
                )
                results.append(plot_data)
            except exceptions.StreamLostError:
                raise
            except exceptions.InvalidChannelCountError:
                raise
            except exceptions.InvalidChannelFormatError:
                raise
            except Exception:
                raise
        return results

    def on_data_updated(
        self, stream_name: str, sample: np.ndarray, channel_labels: List[str]
    ) -> Dict[str, Any]:
        """Handles data updates from DataInlet instances.

        Args:
            stream_name: Identifier for the data source.
            sample: The new data sample as a NumPy array.
            channel_labels: List of labels for each channel in the sample.

        Returns:
            Dictionary containing 'stream_name', 'data', and 'channel_labels'.
        """
        plot_data = {
            "stream_name": stream_name,
            "data": sample.tolist(),
            "channel_labels": channel_labels,
        }
        return plot_data

    def update_channel_visibility(self, channel_name: str, visible: bool) -> None:
        """Updates the visibility of a specific data channel.

        Args:
            channel_name: The unique name of the channel to toggle.
            visible: True to show the channel, False to hide it.
        """
        self.channel_visibility[channel_name] = visible
