"""Module providing the MainAppPresenter class for MoBI_View."""

from typing import Any, Dict, List

from MoBI_View.core import data_inlet, exceptions


class MainAppPresenter:
    """Presenter managing data inlets and delivering plot data.

    This class processes data from DataInlet instances and provides data for
    consumption by external systems (e.g., web servers).

    Attributes:
        data_inlets: A list of DataInlet instances for data acquisition.
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

    def poll_data(self) -> List[Dict[str, Any]]:
        """Polls each DataInlet for new data and returns plot data.

        Returns:
            List of plot data dictionaries, one per inlet that produced new
            samples since the previous poll.

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
                samples, timestamps = inlet.pull_chunk()
                if not samples:
                    continue
                plot_data = self.on_data_updated(
                    inlet.stream_name,
                    inlet.stream_type,
                    samples,
                    timestamps,
                    inlet.channel_info["labels"],
                    inlet.channel_info["units"],
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
        self,
        stream_name: str,
        stream_type: str,
        samples: List[List[Any]],
        timestamps: List[float],
        channel_labels: List[str],
        channel_units: List[str],
    ) -> Dict[str, Any]:
        """Handles data updates from DataInlet instances.

        Args:
            stream_name: Identifier for the data source.
            stream_type: LSL content type for the data source.
            samples: New samples, each a list of per-channel values.
            timestamps: LSL timestamps aligned with `samples`.
            channel_labels: List of labels for each channel in the sample.
            channel_units: List of units for each channel in the sample.

        Returns:
            Dictionary describing the new samples and their channel metadata.
        """
        plot_data = {
            "stream_name": stream_name,
            "stream_type": stream_type,
            "samples": samples,
            "timestamps": timestamps,
            "channel_labels": channel_labels,
            "channel_units": channel_units,
        }
        return plot_data
