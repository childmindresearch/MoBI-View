# MoBI-View Architecture

## Overview

MoBI-View follows a **layered architecture** with clear separation of concerns for real-time LSL stream visualization.

## Architecture Layers

```
┌──────────────────────────────────────────────────────────────┐
│ Application Layer (main.py)                                  │
│ - Discovers LSL streams                                      │
│ - Creates DataInlet instances                                │
│ - Initializes Presenter with DataInlets                      │
│ - Starts WebSocket server                                    │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            ▼
                  ┌─────────────────────┐
                  │ Model Layer         │
                  │ (DataInlet)         │
                  │                     │
                  │ - Connects to ONE   │
                  │   LSL stream        │
                  │ - Buffers samples   │
                  │ - pull_sample()     │
                  └──────────┬──────────┘
                             │
                             ▼
                  ┌─────────────────────┐
                  │ Presenter Layer     │
                  │ (MainAppPresenter)  │
                  │                     │
                  │ - Manages list of   │
                  │   DataInlets        │
                  │ - Polls all inlets  │
                  │ - Formats data      │
                  │ - poll_data()       │
                  └──────────┬──────────┘
                             │
                             ▼
                  ┌─────────────────────┐
                  │ View Layer          │
                  │ (WebServer)         │
                  │                     │
                  │ - Reads from        │
                  │   presenter         │
                  │ - Broadcasts to     │
                  │   WebSocket clients │
                  │ - Handles UI state  │
                  │   (visibility, etc) │
                  └─────────────────────┘
```

**Data Flow**: Application → Model → Presenter → View

- **Application** discovers streams and wires components together
- **Model** (DataInlet) pulls data from LSL streams
- **Presenter** polls models and formats data
- **View** reads from presenter and renders to users

## Component Responsibilities

### 1. Application Layer (`main.py`)

**Purpose**: Entry point that wires everything together

**Responsibilities**:
- Discover LSL streams using `discover_and_create_inlets()`
- Create `DataInlet` instances for each discovered stream
- Initialize `MainAppPresenter` with the inlets
- Start the WebSocket server with `run_server()`
- Schedule browser launch

**Key Functions**:
- `main()` - Main entry point

### 2. Model Layer (`core/data_inlet.py`)

**Purpose**: Represents a single LSL stream connection

**Responsibilities**:
- Connect to ONE LSL stream
- Buffer incoming samples
- Pull samples from the stream
- Provide stream metadata (name, type, channels, sample rate)

**Key Methods**:
- `__init__(partial_info: StreamInfo)` - Create connection
- `pull_sample()` - Pull one sample from the stream
- `get_channel_information()` - Extract channel metadata

**Attributes**:
- `stream_name`, `stream_type`, `source_id` - Stream identifiers
- `buffers` - Circular buffer for samples
- `ptr` - Current position in buffer
- `channel_info` - Channel labels, types, units

### 3. Presenter Layer (`presenters/main_app_presenter.py`)

**Purpose**: Business logic layer that manages multiple streams

**Responsibilities**:
- Manage list of `DataInlet` instances
- Poll all inlets at regular intervals
- Format data for consumption by views
- Manage channel visibility state
- Handle errors from individual streams

**Key Methods**:
- `poll_data()` - Poll all inlets and return formatted data
- `on_data_updated()` - Format sample data for views
- `update_channel_visibility()` - Toggle channel display

**Key Principle**: The presenter does NOT know about LSL or discovery - it just manages DataInlets that are passed to it.

### 4. View Layer (`web/server.py`)

**Purpose**: Pure view - reads from presenter and serves WebSocket clients

**Responsibilities**:
- Serve static HTML/CSS/JS files
- Maintain WebSocket connections
- Read data from presenter's inlets
- Broadcast formatted data to connected clients
- Handle client commands (e.g., discover button)

**Key Components**:
- `Broadcaster` - Periodically reads from presenter and sends to WebSocket clients
- `poll_presenter_continuously()` - Background task that calls `presenter.poll_data()`
- `ws_handler()` - Handle WebSocket connections and messages
- `run_server()` - Main server entry point

**Key Principle**: The server does NOT discover streams or create inlets - it only reads from the presenter.

### 5. Discovery Utilities (`core/discovery.py`)

**Purpose**: Shared utility for discovering LSL streams

**Responsibilities**:
- Call `pylsl.resolve_streams()` to find available streams
- Create `DataInlet` instances for discovered streams
- Deduplicate streams based on (source_id, name, type)
- Handle errors during inlet creation

**Key Functions**:
- `discover_and_create_inlets()` - Returns list of new DataInlet instances

**Usage**: Called by application layer (main.py) and by WebSocket handler when user clicks "Discover Streams" button

## Data Flow

### Startup Flow

```
main.py
  ├─> discover_and_create_inlets()
  │     └─> resolve_streams()  (pylsl)
  │     └─> DataInlet(info)  for each stream
  │
  ├─> MainAppPresenter(data_inlets=[...])
  │     └─> _initialize_channels()
  │
  └─> run_server(presenter)
        ├─> start_http_static_server()
        ├─> poll_presenter_continuously()
        │     └─> presenter.poll_data()  (every 2ms)
        │           └─> inlet.pull_sample()  for each inlet
        │
        └─> Broadcaster._run()
              └─> Read from presenter.data_inlets
              └─> ws.send(json)  to all clients
```

### Runtime Data Flow (Polling)

```
[LSL Stream] ──samples──> [DataInlet.pull_sample()]
                                │
                                ├─> Store in buffers[ptr]
                                │
                          [Presenter.poll_data()]
                                │
                                ├─> Read buffers[latest_index]
                                ├─> Format as dict
                                │
                          [Broadcaster._run()]
                                │
                                └─> Send to WebSocket clients
```

### User-Triggered Discovery Flow

```
[User clicks "Discover Streams" button]
          │
          ▼
    [WebSocket message: {type: "discover_streams"}]
          │
          ▼
    [ws_handler()]
          │
          ├─> discover_and_create_inlets()
          │     └─> resolve_streams()
          │     └─> Create new DataInlets
          │
          ├─> Append new inlets to presenter.data_inlets
          ├─> Initialize channel_visibility
          │
          └─> Send response: {type: "discover_result", count: X}
```

## Key Architectural Decisions

### 1. No Discovery in Presenter

The presenter does NOT discover streams. Discovery happens at the application layer (main.py) or through user action (discover button).

**Rationale**: Presenter is business logic layer, not responsible for I/O or system initialization.

### 2. No Discovery in Server

The server does NOT discover streams automatically. It only handles user-triggered discovery via WebSocket commands.

**Rationale**: Server is pure view layer, should not contain business logic or know about LSL.

### 3. Mutable Inlet List

The `presenter.data_inlets` list is mutable and can be appended to directly. No need for `add_inlet()` method.

**Rationale**: Simple and direct. The presenter initializes channel visibility in `__init__`, and the WebSocket handler can manually initialize visibility for new inlets.

### 4. Separation of Concerns

- **DataInlet**: ONE stream, ONE responsibility (buffer samples)
- **Presenter**: Coordinate MULTIPLE inlets, format data
- **Server**: Read from presenter, serve to clients
- **Application**: Wire everything together

### 5. Discovery Utility

Shared `discover_and_create_inlets()` function used by both:
- Startup (main.py)
- Runtime (WebSocket handler when user clicks discover button)


## Channel Color Configuration

The visualization uses a **pattern-based color assignment system** located in `web/static/colors.js`:

**Key Features:**
- **Pattern Matching**: Channel names are matched against regex patterns (e.g., `/^c\d+$/i` for C3, C4, etc.)
- **Pre-configured Sensor Types**: Includes EEG, EMG, EOG, ECG, accelerometer, gyroscope, and more
- **Customizable**: Users can edit `colors.js` to add custom patterns or change colors
- **Deterministic**: Same channel name always gets same color across sessions
- **Fallback Hash**: If no pattern matches, color is generated from channel name hash

**Example Usage:**
```javascript
// In colors.js - add custom pattern
{ 
  pattern: /^mydevice/i,           // Matches "MyDevice_1", "mydevice_A"
  color: 'hsl(180, 80%, 55%)',    // Teal color
  description: 'My custom device'  // Documentation
}
```

**Benefits:**
- **Semantic Grouping**: Related channels get similar colors (e.g., all frontal EEG in blue)
- **Readable Configuration**: HSL format is intuitive (hue, saturation, lightness)
- **Flexible Matching**: Supports wildcards, regex, case-insensitive matching
- **Well-Documented**: See `README_COLORS.md` for complete customization guide
