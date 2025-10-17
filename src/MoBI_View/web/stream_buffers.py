"""Registry for sharing live LSL inlets between server components."""

from __future__ import annotations

from typing import Dict, List

from MoBI_View.core.data_inlet import DataInlet


class Registry:
    """Store live ``DataInlet`` objects so other services can look them up."""

    def __init__(self) -> None:
        """Start with an empty mapping of stream name to inlet."""
        self.streams: Dict[str, DataInlet] = {}

    def add(self, inlet: DataInlet) -> None:
        """Register a new data inlet.

        Args:
            inlet: Data inlet to add to the registry.
        """
        self.streams[inlet.stream_name] = inlet

    def get(self, name: str) -> DataInlet:
        """Retrieve an inlet by stream name.

        Args:
            name: Name of the stream to look up.

        Returns:
            The matching data inlet.

        Raises:
            KeyError: If no inlet has been registered under ``name``.
        """
        try:
            return self.streams[name]
        except KeyError as exc:
            raise KeyError(f"Stream '{name}' not found in registry") from exc

    def remove(self, name: str) -> None:
        """Remove an inlet.

        Args:
            name: Name of the stream to remove.

        Raises:
            KeyError: If the stream is not registered.
        """
        try:
            del self.streams[name]
        except KeyError as exc:
            raise KeyError(f"Stream '{name}' not found in registry") from exc

    def all(self) -> List[DataInlet]:
        """Return a list of all registered inlets.

        Returns:
            List of registered data inlets.
        """
        return list(self.streams.values())
