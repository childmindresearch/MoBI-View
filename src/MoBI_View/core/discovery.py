"""Stream discovery utilities for MoBI-View.

This module provides shared functions for discovering LSL streams and creating
DataInlets. These functions are used by:
- Application layer (main.py) at startup to initialize the system.
- View layer (server.py) when the user clicks "Discover Streams" button.

The key function is discover_and_create_inlets(), which:
1. Calls pylsl.resolve_streams() to find available LSL streams.
2. Deduplicates against existing inlets using (source_id, name, type) tuple.
3. Creates a new DataInlet for each unique stream.
4. Returns the list of new inlets.
"""

from typing import List, Optional, Set

from pylsl import info as pylsl_info
from pylsl import resolve as pylsl_resolve

from MoBI_View.core import config, data_inlet


def discover_and_create_inlets(
    wait_time: Optional[float] = None,
    existing_inlets: Optional[List[data_inlet.DataInlet]] = None,
) -> List[data_inlet.DataInlet]:
    """Discover LSL streams and create DataInlet instances.

    Resolves available LSL streams and creates DataInlet instances for new streams
    not in existing_inlets. Deduplication is based on (source_id, stream_name,
    stream_type) tuple.

    Args:
        wait_time: How long to wait for LSL network discovery in seconds. If None,
            uses Config.STREAM_RESOLVE_WAIT_TIME (default 1.0s per LSL recommendations).
        existing_inlets: Optional list of existing DataInlets to check for duplicates.

    Returns:
        List of new DataInlet instances created.
    """
    new_inlets: List[data_inlet.DataInlet] = []

    existing_streams: Set[tuple[str, str, str]] = set()
    if existing_inlets:
        existing_streams = {
            (inlet.source_id, inlet.stream_name, inlet.stream_type)
            for inlet in existing_inlets
        }

    if wait_time is None:
        wait_time = config.Config.STREAM_RESOLVE_WAIT_TIME

    try:
        discovered_streams: List[pylsl_info.StreamInfo] = pylsl_resolve.resolve_streams(
            wait_time
        )

        for info in discovered_streams:
            try:
                stream_id = (info.source_id(), info.name(), info.type())

                if stream_id in existing_streams:
                    continue

                inlet = data_inlet.DataInlet(info)
                new_inlets.append(inlet)
                existing_streams.add(stream_id)

                print(
                    f"Discovered new stream: {info.name()} "
                    f"({info.type()}, {inlet.channel_count} channels)"
                )

            except Exception as err:
                stream_name = getattr(info, "name", lambda: "unknown")()
                print(f"Skipping stream {stream_name}: {err}")
                continue

    except Exception as err:
        print(f"Error during stream discovery: {err}")

    return new_inlets
