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

import logging
from typing import List, Optional, Set

from pylsl import info as pylsl_info
from pylsl import resolve as pylsl_resolve

from MoBI_View.core import config, data_inlet

logger = logging.getLogger("MoBI-View.core.discovery")


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

    if not isinstance(wait_time, (int, float)) or wait_time == float("inf"):
        logger.warning("Invalid wait_time value (%s), using default 1.0s", wait_time)
        wait_time = 1.0
    elif wait_time <= 0:
        logger.warning(
            "wait_time cannot be negative or zero (%s), setting to 1.0s", wait_time
        )
        wait_time = 1.0
    elif wait_time < 0.5:
        logger.warning(
            "wait_time (%s) below minimum of 0.5s, setting to 0.5s", wait_time
        )
        wait_time = 0.5

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

                logger.info(
                    "Discovered new stream: %s (%s, %d channels)",
                    info.name(),
                    info.type(),
                    inlet.channel_count,
                )

            except Exception as err:
                stream_name = getattr(info, "name", lambda: "unknown")()
                logger.warning("Skipping stream %s: %s", stream_name, err)
                continue

    except Exception as err:
        logger.error("Error during stream discovery: %s", err)

    return new_inlets
