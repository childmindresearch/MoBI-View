"""Module providing the main entry point for the MoBI_View application.

This module discovers all available LSL streams, creates DataInlet objects for each,
and prints stream information. The Qt-based desktop UI has been removed.
Usage:
    python -m MoBI_View.main
"""

from typing import List

from pylsl import resolve_streams

from MoBI_View.core.data_inlet import DataInlet


def main() -> None:
    """Discovers and lists available LSL streams."""
    print("Resolving LSL streams...")

    discovered_streams = resolve_streams()
    data_inlets: List[DataInlet] = []

    for info in discovered_streams:
        try:
            inlet = DataInlet(info)
            data_inlets.append(inlet)
            print(
                f"Discovered stream: Name={inlet.stream_name}, "
                f"Type={inlet.stream_type}, "
                f"Channels={inlet.channel_count}"
            )
            print(f"  Channel labels: {', '.join(inlet.channel_info['labels'])}")
        except Exception as err:
            print(f"Skipping stream {info.name()} due to: {err}")

    if not data_inlets:
        print("No valid LSL streams found.")
    else:
        print(f"\nTotal streams discovered: {len(data_inlets)}")
        print("\nNote: Desktop Qt UI has been removed.")
        print("For visualization, please use the web-based interface.")


if __name__ == "__main__":
    main()
