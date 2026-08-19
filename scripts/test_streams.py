# /// script
# dependencies = [
#   "pylsl",
#   "numpy",
# ]
# ///

"""Simulated LSL streams for exercising the MoBI-View UI.

Publishes four concurrent outlets with populated channel metadata:
    1. GazeStream - 4 channels at 60 Hz.
    2. EEGStream - 21 channels (10-20 system) at 250 Hz.
    3. PhysioStream - 5 channels at 100 Hz.
    4. AudioMarkerStream - single-channel string markers at 10 Hz.

Run this before starting MoBI-View so the streams are discoverable.
"""

import sys
import threading
import time

import numpy as np
from pylsl import StreamInfo, StreamOutlet


def create_gaze_stream() -> None:
    """Publishes a 60 Hz gaze stream with position, pupil, and confidence."""
    channel_labels = ["Gaze_X", "Gaze_Y", "PupilDiameter", "GazeConfidence"]
    info = StreamInfo(
        name="GazeStream",
        type="Gaze",
        channel_count=len(channel_labels),
        channel_format="float32",
        nominal_srate=60,
        source_id="gaze_stream_001",
    )

    channels_node = info.desc().append_child("channels")
    units = ["deg", "deg", "mm", "percent"]
    for label, unit in zip(channel_labels, units):
        channel = channels_node.append_child("channel")
        channel.append_child_value("label", label)
        channel.append_child_value("unit", unit)

    outlet = StreamOutlet(info)
    print("GazeStream created and sending data...")

    while True:
        elapsed = time.time()
        sample = [
            20 * np.sin(2 * np.pi * 0.3 * elapsed) + np.random.normal(0, 1.5),
            20 * np.cos(2 * np.pi * 0.2 * elapsed) + np.random.normal(0, 1.5),
            5 + np.sin(2 * np.pi * 0.15 * elapsed) + np.random.normal(0, 0.1),
            np.random.uniform(80, 100),
        ]
        outlet.push_sample(sample)
        time.sleep(1.0 / 60.0)


def create_eeg_stream() -> None:
    """Publishes a 250 Hz, 21-channel EEG stream in microvolts."""
    eeg_channels = [
        "Fp1", "Fp2", "F7", "F3", "Fz", "F4", "F8",
        "T7", "C3", "Cz", "C4", "T8",
        "P7", "P3", "Pz", "P4", "P8",
        "O1", "O2", "A1", "A2",
    ]

    info = StreamInfo(
        name="EEGStream",
        type="EEG",
        channel_count=len(eeg_channels),
        channel_format="float32",
        nominal_srate=250,
        source_id="eeg_stream_001",
    )

    channels_node = info.desc().append_child("channels")
    for label in eeg_channels:
        channel = channels_node.append_child("channel")
        channel.append_child_value("label", label)
        channel.append_child_value("unit", "microvolts")

    outlet = StreamOutlet(info)
    print("EEGStream created and sending data...")

    posterior = {"O1", "O2", "P3", "P4", "Pz", "P7", "P8"}
    frontal = {"Fp1", "Fp2", "F7", "F3", "Fz", "F4", "F8"}
    temporal = {"T7", "T8"}

    while True:
        now = time.time()
        sample = []
        for index, channel in enumerate(eeg_channels):
            if channel in {"A1", "A2"}:
                sample.append(np.random.normal(0, 5))
                continue

            phase = index * 0.4
            voltage = np.random.normal(0, 12)
            if channel in posterior:
                voltage += 30 * np.sin(2 * np.pi * 10 * now + phase)
            if channel in frontal:
                voltage += 15 * np.sin(2 * np.pi * 20 * now + phase)
            if channel in temporal:
                voltage += 20 * np.sin(2 * np.pi * 6 * now + phase)
            if np.random.random() < 0.001:
                voltage += np.random.normal(0, 100)
            sample.append(voltage)

        outlet.push_sample(sample)
        time.sleep(1.0 / 250.0)


def create_physiological_stream() -> None:
    """Publishes a 100 Hz physiological stream with five channels."""
    physio_channels = [
        ("HeartRate", "bpm"),
        ("SkinConductance", "microsiemens"),
        ("BreathingRate", "breaths/min"),
        ("BloodPressure", "mmHg"),
        ("BodyTemperature", "degC"),
    ]
    info = StreamInfo(
        name="PhysioStream",
        type="Physiological",
        channel_count=len(physio_channels),
        channel_format="float32",
        nominal_srate=100,
        source_id="physio_stream_001",
    )

    channels_node = info.desc().append_child("channels")
    for label, unit in physio_channels:
        channel = channels_node.append_child("channel")
        channel.append_child_value("label", label)
        channel.append_child_value("unit", unit)

    outlet = StreamOutlet(info)
    print("PhysioStream created and sending data...")

    while True:
        now = time.time()
        sample = [
            75 + 8 * np.sin(2 * np.pi * 0.2 * now) + np.random.normal(0, 1),
            2.5 + 1.2 * np.sin(2 * np.pi * 0.05 * now) + np.random.normal(0, 0.1),
            16 + 3 * np.sin(2 * np.pi * 0.25 * now) + np.random.normal(0, 0.3),
            100 + 12 * np.sin(2 * np.pi * 0.1 * now) + np.random.normal(0, 1),
            37.0 + 0.3 * np.sin(2 * np.pi * 0.02 * now) + np.random.normal(0, 0.02),
        ]
        outlet.push_sample(sample)
        time.sleep(1.0 / 100.0)


def create_audio_stream() -> None:
    """Publishes a 10 Hz single-channel string marker stream."""
    info = StreamInfo(
        name="AudioMarkerStream",
        type="Markers",
        channel_count=1,
        channel_format="string",
        source_id="audio_marker_stream_001",
    )

    channels_node = info.desc().append_child("channels")
    channel = channels_node.append_child("channel")
    channel.append_child_value("label", "Marker")
    channel.append_child_value("unit", "label")

    outlet = StreamOutlet(info)
    print("AudioMarkerStream created and sending marker strings...")

    marker_types = ["beep", "silence", "speech_start", "speech_end", "annotation"]
    while True:
        outlet.push_sample([str(np.random.choice(marker_types))])
        time.sleep(0.1)


def main() -> None:
    """Starts every simulated stream on its own daemon thread."""
    targets = (
        create_gaze_stream,
        create_eeg_stream,
        create_physiological_stream,
        create_audio_stream,
    )
    for target in targets:
        threading.Thread(target=target, daemon=True).start()

    print("All test streams are running. Press Ctrl+C to exit.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Test streams stopped.")
        sys.exit(0)


if __name__ == "__main__":
    main()
