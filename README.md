# `MoBI-View`

A real-time biosignal visualization tool for Lab Streaming Layer (LSL) streams.

[![Build](https://github.com/childmindresearch/MoBI-View/actions/workflows/test.yaml/badge.svg?branch=main)](https://github.com/childmindresearch/MoBI-View/actions/workflows/test.yaml?query=branch%3Amain)
[![codecov](https://codecov.io/gh/childmindresearch/MoBI-View/branch/main/graph/badge.svg?token=22HWWFWPW5)](https://codecov.io/gh/childmindresearch/MoBI-View)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
![stability-stable](https://img.shields.io/badge/stability-stable-green.svg)
[![LGPL--2.1 License](https://img.shields.io/badge/license-LGPL--2.1-blue.svg)](https://github.com/childmindresearch/MoBI-View/blob/main/LICENSE)
[![pages](https://img.shields.io/badge/api-docs-blue)](https://childmindresearch.github.io/MoBI-View)

> **LSL setup issue?** `pylsl` still requires the native `liblsl` shared
> library on macOS and Linux. If import or stream discovery fails, go directly
> to [liblsl troubleshooting](#liblsl-troubleshooting).

Welcome to `MoBI-View`, a Python application designed for real-time visualization of biosignal data from Lab Streaming Layer (LSL) streams. This tool allows researchers and clinicians to monitor and analyze various biosignals like EEG, eye-tracking data, and other physiological measurements through an intuitive and responsive interface.

## Demo

<p align="center">
    <img src=".github/assets/mobiview_demo_small.gif" alt="MoBI-View live stream visualization dashboard" width="85%" />
</p>

## Features

- Real-time visualization from any LSL-compatible numeric stream.
- Browser UI served by the Python application over HTTP and WebSocket.
- All-stream overview plus a focused page for each discovered stream.
- EEG streams separated from gaze, physiological, and marker streams.
- uPlot charts with a rolling history and responsive resizing.
- Per-channel visibility toggles, show-all/hide-all controls, and latest readings.
- Stacked EEG channel view for high-channel-count signals.
- String marker streams rendered as an event timeline.
- Automatic discovery at startup and on-demand discovery from the UI.

## Installation

### Installing uv

First, install uv, a fast package installer and resolver for Python:

**macOS/Linux**:
```sh
curl --proto '=https' --tlsv1.2 -sSf https://astral.sh/uv/install.sh | sh
```

**Windows (Powershell)**:
```sh
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Installing MoBI-View

Option 1: Install from PyPI

```sh
pip install mobi-view
```

Option 2: Install from Github

```sh
# Clone the repository
git clone https://github.com/childmindresearch/MoBI-View.git
cd MoBI-View

# Optional: Create virtual environment
uv venv

# Optional: Activate the environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install all dependencies including the package itself
uv sync
```

## Quick Start Guide

MoBI-View is currently a browser application. The Python process discovers LSL
streams, polls them, and serves the Svelte/uPlot frontend at `http://localhost:8765`.

### Run the supplied test streams

Use a separate terminal from the application terminal. From the repository root:

```sh
uv run scripts/test_streams.py
```

Leave this process running. It publishes these streams:

| Stream | Type | Channels | Rate |
| --- | --- | ---: | ---: |
| `GazeStream` | Gaze | 4 | 60 Hz |
| `EEGStream` | EEG | 21 | 250 Hz |
| `PhysioStream` | Physiological | 5 | 100 Hz |
| `AudioMarkerStream` | Markers | 1 string channel | 10 Hz |

### Run the application

In a second terminal, from the repository root:

```sh
uv sync
uv run mobi-view
```

The application opens the browser automatically. If it does not, open
`http://localhost:8765` manually.

The initial discovery happens when MoBI-View starts. If the test streams were
started after MoBI-View, click **Discover** in the upper-right corner of the
dashboard. You should then see **All streams** in the overview, `EEGStream` in
the EEG section, and the gaze, physiological, and marker streams in the Streams
section.

### Use the dashboard

- **All streams** shows a compact live panel for every discovered stream.
- Select a stream in the sidebar to open its full-size view.
- Use the channel checkboxes below each chart to toggle individual channels.
- Use the checkmark and square-X buttons to show or hide all channels.
- Use the stacked-view button on EEG or other high-channel-count streams to
    give each visible channel its own baseline.
- Marker streams display their latest string events instead of a numeric chart.
- **Clear** clears the browser history without disconnecting the streams.

### Rebuild after frontend changes

The Python server serves the static bundle in `src/MoBI_View/web/static`. After
changing anything under `frontend/src`, rebuild before launching MoBI-View:

```sh
cd frontend
npm install
npm run check
npm run build
cd ..
uv run mobi-view
```

For frontend-only development, start the Python server first, then run:

```sh
cd frontend
npm run dev
```

Open the Vite URL printed in the terminal. Its WebSocket connection still
expects the Python server at `ws://localhost:8765`.

### Troubleshooting

- **No streams appear:** confirm `uv run scripts/test_streams.py` is still
    running, then click **Discover**. LSL discovery normally takes about one
    second.
- **The browser shows an old layout:** stop the application, run
    `npm run build` from `frontend`, restart `uv run mobi-view`, and hard-refresh
    `http://localhost:8765` with `Cmd+Shift+R`.
- **The sidebar says disconnected:** make sure the page is loaded from
    `http://localhost:8765`, not from a local HTML file. Check that the Python
    process is listening on port `8765`.
- **The test streams stop:** press `Ctrl+C` only in the test-stream terminal;
    restart it and click **Discover** in the browser.

## Application Interface

When you launch `MoBI-View`:

1. **Stream Discovery**: Available LSL streams are discovered at startup and
    can be refreshed with **Discover**.
2. **Overview**: **All streams** provides a compact live view of every stream.
3. **Stream pages**: The sidebar opens a full-size page for each stream, with
    EEG streams grouped separately.
4. **Channel selection**: Toggle individual channels directly below each chart,
    or use the show-all/hide-all controls.
5. **Live transport**: Samples are sent from Python to the browser in timestamped
    WebSocket frames. Numeric samples are plotted in uPlot; string markers appear
    in the marker event feed.

## liblsl Troubleshooting

`pylsl` is the Python wrapper, not the native LSL runtime. Current `pylsl`
releases still require a `liblsl` shared library on macOS and Linux. Windows
packages commonly include the native library, but this varies by Python and
package combination. See the [official pylsl installation notes](https://github.com/labstreaminglayer/pylsl#installation)
and [liblsl releases](https://github.com/sccn/liblsl/releases) for upstream
details.

You only need this section if `uv run mobi-view` fails while importing `pylsl`,
or if LSL discovery fails before the browser opens. The frontend itself does
not need liblsl.

### macOS

The simplest route is Homebrew:

```sh
brew install labstreaminglayer/tap/lsl
uv run python -c "import pylsl; print('pylsl/liblsl OK')"
```

If liblsl is installed somewhere nonstandard, point `pylsl` at it explicitly:

```sh
export PYLSL_LIB=/path/to/liblsl.dylib
uv run python -c "import pylsl; print('pylsl/liblsl OK')"
```

### Linux

Install liblsl through your distribution or Conda, then verify the import:

```sh
conda install -c conda-forge liblsl
uv run python -c "import pylsl; print('pylsl/liblsl OK')"
```

For a library in a custom location, use `PYLSL_LIB` with the full shared-library
path, for example:

```sh
export PYLSL_LIB=/usr/local/lib/liblsl.so
uv run python -c "import pylsl; print('pylsl/liblsl OK')"
```

After the import check succeeds, restart both `scripts/test_streams.py` and
`uv run mobi-view`, then click **Discover** in the browser.

## Future Directions

- Custom filtering and signal processing options.
- Extended analysis tools for common biosignal metrics.
- EEG impedance checker for ease of setup.
