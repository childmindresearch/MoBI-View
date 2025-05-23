[![DOI](https://zenodo.org/badge/657341621.svg)](https://zenodo.org/doi/10.5281/zenodo.10383685)

# `MoBI-View`

A real-time biosignal visualization tool for Lab Streaming Layer (LSL) streams.

[![Build](https://github.com/childmindresearch/MoBI-View/actions/workflows/test.yaml/badge.svg?branch=main)](https://github.com/childmindresearch/MoBI-View/actions/workflows/test.yaml?query=branch%3Amain)
[![codecov](https://codecov.io/gh/childmindresearch/MoBI_View/branch/main/graph/badge.svg?token=22HWWFWPW5)](https://codecov.io/gh/childmindresearch/MoBI-View)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
![stability-stable](https://img.shields.io/badge/stability-stable-green.svg)
[![LGPL--2.1 License](https://img.shields.io/badge/license-LGPL--2.1-blue.svg)](https://github.com/childmindresearch/MoBI-View/blob/main/LICENSE)
[![pages](https://img.shields.io/badge/api-docs-blue)](https://childmindresearch.github.io/MoBI_View)

Welcome to `MoBI-View`, a Python application designed for real-time visualization of biosignal data from Lab Streaming Layer (LSL) streams. This tool allows researchers and clinicians to monitor and analyze various biosignals like EEG, accelerometer data, and other physiological measurements through an intuitive and responsive interface.

## Features

- Real-time signal visualization from any LSL-compatible device streaming numerical data
- Multi-stream support for simultaneous monitoring of different data sources
- Specialized plot types optimized for different signal types:
- EEG plot widgets for neurophysiological data
- Numeric plot widgets for other sensor data
- Channel / Stream visibility control for focusing on specific data channels
- Hierarchical stream organization through a tree-based interface
- Automatic stream discovery

## Installation

Install this package via :

```sh
pip install MoBI_View
```

Or get the newest development version via:

```sh
pip install git+https://github.com/childmindresearch/MoBI-View
```

## Dependencies

`MoBI-View` requires:

- Python 3.9+
- PyQt6
- pylsl (Lab Streaming Layer)
- numpy

## Quick start

Launch `MoBI-View` to automatically discover and visualize LSL streams available in your current network.

```Python
import MoBI_View

MoBI_View.main()
```

**Command Line Usage**

You can also start `MoBI-View` directly from the command line

```sh
poetry run mobi-view
```

## Application Interface

When you launch `MoBI-View`:

1. **Stream Discovery**: The application automatically discovers available LSL streams.
2. **Visualization**: Streams are displayed in appropriate plot widgets based on their type (EEG vs non-EEG).
3. **Control Panel**: A tree view on the left shows available streams and channels. This control panel can be moved or seperated out of the main window.
4. **Channel Selection**: Toggle visibility of individual channels by clicking on their boxes in the Control Panel.

## Future Directions

- Support for additional visualization types (non-numeric data and event markers).
- Custom filtering and signal processing options.
- Extended analysis tools for common biosignal metrics.
- EEG impedance checker for ease of setup.

