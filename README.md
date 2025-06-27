# `MoBI-View`

A real-time biosignal visualization tool for Lab Streaming Layer (LSL) streams.

[![Build](https://github.com/childmindresearch/MoBI-View/actions/workflows/test.yaml/badge.svg?branch=main)](https://github.com/childmindresearch/MoBI-View/actions/workflows/test.yaml?query=branch%3Amain)
[![codecov](https://codecov.io/gh/childmindresearch/MoBI-View/branch/main/graph/badge.svg?token=22HWWFWPW5)](https://codecov.io/gh/childmindresearch/MoBI-View)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
![stability-stable](https://img.shields.io/badge/stability-stable-green.svg)
[![LGPL--2.1 License](https://img.shields.io/badge/license-LGPL--2.1-blue.svg)](https://github.com/childmindresearch/MoBI-View/blob/main/LICENSE)
[![pages](https://img.shields.io/badge/api-docs-blue)](https://childmindresearch.github.io/MoBI-View)

Welcome to `MoBI-View`, a Python application designed for real-time visualization of biosignal data from Lab Streaming Layer (LSL) streams. This tool allows researchers and clinicians to monitor and analyze various biosignals like EEG, eye-tracking data, and other physiological measurements through an intuitive and responsive interface.

## Features

- Real-time signal visualization from any LSL-compatible device streaming numerical data.
- Multi-stream support for simultaneous monitoring of different data sources.
- Specialized plot types optimized for different signal types.
- EEG plot widgets for neurophysiological data.
- Numeric plot widgets for other sensor data.
- Channel / Stream visibility control for focusing on specific data channels.
- Hierarchical stream organization through a tree-based interface.
- Automatic stream discovery.

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

> ### ⚠️ Import Note for MoBI-View Installation
>`MoBI-View` depends on pylsl, which utilizes liblsl, a system-level dependency that is not installed by default. Install it by following the instructions from the `Installing liblsl` section below.

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

> ### ⚠️ Installing liblsl
>
>The pylsl package requires the liblsl binaries for your platform. You can install them using one of the following methods:
>
>
>##### Option 1: Package Managers
>
>- **Conda** (all platforms): `conda install -c conda-forge liblsl`
>- **vcpkg** (Windows/Linux): `vcpkg install liblsl`
>- **Conan** (Windows): `conan install liblsl`
>- **Homebrew** (macOS): `brew install labstreaminglayer/tap/lsl`
>
>##### Option 2: Build from Source
>
>```sh
>git clone --depth=1 https://github.com/sccn/liblsl.git
>cd liblsl
>mkdir build && cd build
>cmake ..
>cmake --build . --config Release
>cmake --install .
>```
>
>##### Option 3: Precompiled Binaries
>
>- Download the latest release for your platform from the [liblsl Releases page](https://github.com/sccn/liblsl/releases)
>- Extract the zip file and add the library to your system's path:
>
>**Windows**: 
>1. Download the Windows ZIP file (e.g., `liblsl-1.16.2-Win64.zip`)
>2. Extract the Zip file, which contains:
    - `bin/lsl.dll`
    - `lib/lsl.dll`
    - header files in `include/` directory
>3. Add the extracted `bin` directory to your PATH environment variable
>
>```sh
># Example: If unzipped to C:\liblsl
>$env:PATH += ";C:\liblsl\bin"
>```
>
>**macOS**:
>1. Download the macOS package (e.g., `liblsl-1.16.2-OSX-amd64.tar.bz2`)
>2. Extract the archive:
>```sh
>tar -xf liblsl-1.16.2-OSX-amd64.tar.bz2
>```
>3. Inside you'll find:
    - `lib/liblsl.dylib`
    - header files in `include/` directory
>4. You can either:
    - Copy `lib/liblsl.dylib` to `lib`
    - Or set the `DYLD_LIBRARY_PATH` to include the lib directory
>
>**Linux**:
>1. Download the appropriate Debian package (e.g., `liblsl-1.16.2-Linux64-focal.deb` for Ubuntu 20.04)
>2. Install using:
>```sh
>sudo dpkg -i liblsl-1.16.2-Linux64-focal.deb
>```
>
>Or download the liblsl-1.16.2-Linux64.tar.bz2 and extract:
>
>```sh
>tar -xf liblsl-1.16.2-Linux64.tar.bz2
>sudo cp lib/liblsl.so* /usr/local/lib/
>sudo ldconfig
>```

## Quick start Guide

1. **Activate your environment** (if not already activated):

2. **Run MoBI-View** (either method works):
```sh
# Method 1: Using uv run
uv run mobi-view

# Method 2: Direct execution
python -m src/main.py
```

3. Select LSL streams from the tree view to visualize data:
    - EEG data appears in the EEG tab.
    - Other physiological signals appear in the Numeric tab.
    - Toggle streams and channels on/off by clicking checkboxes.


<img src="https://media.githubusercontent.com/media/childmindresearch/MoBI-View/main/.github/assets/mobiview_demo_small.gif" align="center" width="85%"/>

## Application Interface

When you launch `MoBI-View`:

1. **Stream Discovery**: The application automatically discovers available LSL streams.
2. **Visualization**: Streams are displayed in appropriate plot widgets based on their type (EEG vs non-EEG).
3. **Control Panel**: A tree view on the left shows available streams and channels. This control panel can be moved or separated out of the main window.
4. **Channel Selection**: Toggle visibility of individual channels by clicking on their boxes in the Control Panel.

## Future Directions

- Support for additional visualization types (non-numeric data and event markers).
- Custom filtering and signal processing options.
- Extended analysis tools for common biosignal metrics.
- EEG impedance checker for ease of setup.
