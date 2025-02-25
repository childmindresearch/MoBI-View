"""This module contains the interfaces for the view component of the MoBI GUI."""

from typing import Protocol


class IMainAppView(Protocol):
    """Interface for the Main Application View.

    This interface outlines the methods that the MainAppPresenter will interact with
    in the View component (MainAppWindow).
    """

    def update_plot(self, data: dict) -> None:
        """Updates the plot with new data.

        Args:
            data: A dictionary containing the data to be plotted. Expected format:
                {
                    "stream_name": str,
                    "data": List[float] or List[List[float]]
                }
        """

    def set_plot_channel_visibility(self, channel_name: str, visible: bool) -> None:
        """Toggles the visibility of a channel in the plot.

        Args:
            channel_name: The name of the channel to toggle.
            visible: A boolean indicating whether the channel should be visible.
        """

    def display_error(self, message: str) -> None:
        """Displays an error message to the user.

        Args:
            message: The error message to display.
        """

    def add_tree_item(self, stream_name: str, channel_name: str) -> None:
        """Adds a channel entry to the control panel tree.

        Args:
            stream_name: Name of the LSL stream (e.g. "EEGStream").
            channel_name: The fully qualified channel name (e.g. "EEGStream:Fz").
        """
