/**
 * Client-side WebSocket connection and rolling history for LSL streams.
 *
 * History arrays are deliberately kept outside of Svelte's reactive proxies:
 * at 250 Hz with 20+ channels, deep proxying every sample is far too costly.
 * Instead the arrays are mutated in place and a `revision` counter, bumped at
 * most once per animation frame, drives re-rendering.
 */

import type {
  ConnectionStatus,
  IncomingFrame,
  IncomingStream,
  StreamState,
} from "./stream-types.js";

/** Samples retained per channel; ~5 s of a 250 Hz stream. */
const MAX_POINTS = 1250;
/** Marker events retained per marker stream. */
const MAX_MARKERS = 250;
/** Delay before retrying a dropped connection, in milliseconds. */
const RECONNECT_DELAY_MS = 1500;

/**
 * Resolves the WebSocket URL for the Python server.
 *
 * In production the SvelteKit bundle is served by that same server, so the
 * page origin is reused. During `vite dev` the frontend runs on its own port
 * and must reach the default backend port explicitly.
 *
 * @returns The WebSocket URL to connect to.
 */
export function resolveSocketUrl(): string {
  if (import.meta.env.DEV) return "ws://localhost:8765";
  const scheme = location.protocol === "https:" ? "wss" : "ws";
  return `${scheme}://${location.host}`;
}

/**
 * Creates an empty history container for a newly seen stream.
 *
 * @param incoming - The first frame entry received for the stream.
 * @returns A zeroed `StreamState` sized to the stream's channel count.
 */
function createStreamState(incoming: IncomingStream): StreamState {
  const labels = incoming.channel_labels ?? [];
  const type = incoming.stream_type || "Unknown";
  const firstRow = incoming.samples[0] ?? [];
  const isMarker =
    type.toLowerCase().includes("marker") ||
    firstRow.some((value) => typeof value === "string");

  return {
    name: incoming.stream_name,
    type,
    labels,
    units: incoming.channel_units ?? labels.map(() => "unknown"),
    timestamps: [],
    values: labels.map(() => []),
    latest: labels.map(() => (isMarker ? "" : Number.NaN)),
    markers: [],
    sampleCount: 0,
    firstTimestamp: 0,
    lastTimestamp: 0,
    isMarker,
    isEeg: type.toLowerCase() === "eeg",
  };
}

/**
 * Appends a frame's samples to a stream's rolling history.
 *
 * @param state - The stream history to extend, mutated in place.
 * @param incoming - The frame entry holding new samples and timestamps.
 */
function appendSamples(state: StreamState, incoming: IncomingStream): void {
  const { samples, timestamps } = incoming;
  if (samples.length === 0) return;

  for (let i = 0; i < samples.length; i += 1) {
    const row = samples[i];
    const timestamp = timestamps[i] ?? 0;

    if (state.isMarker) {
      state.markers.push({ timestamp, value: String(row[0] ?? "") });
    } else {
      state.timestamps.push(timestamp);
      for (let channel = 0; channel < state.values.length; channel += 1) {
        const value = Number(row[channel]);
        state.values[channel].push(Number.isFinite(value) ? value : Number.NaN);
      }
    }
    state.latest = row;
  }

  if (state.firstTimestamp === 0) state.firstTimestamp = timestamps[0] ?? 0;
  state.lastTimestamp = timestamps[timestamps.length - 1] ?? state.lastTimestamp;
  state.sampleCount += samples.length;

  // Trim once per frame rather than per sample; shift() per sample is O(n²).
  const overflow = state.timestamps.length - MAX_POINTS;
  if (overflow > 0) {
    state.timestamps.splice(0, overflow);
    for (const column of state.values) column.splice(0, overflow);
  }
  const markerOverflow = state.markers.length - MAX_MARKERS;
  if (markerOverflow > 0) state.markers.splice(0, markerOverflow);
}

/** Owns the WebSocket lifecycle and the per-stream rolling histories. */
export class StreamStore {
  /** Discovered streams; reassigned only when the stream set changes. */
  streams = $state.raw<StreamState[]>([]);
  /** Bumped once per animation frame to signal new samples arrived. */
  revision = $state(0);
  /** Current WebSocket connection state. */
  status = $state<ConnectionStatus>("connecting");
  /** True while a `discover` command is awaiting its reply. */
  discovering = $state(false);
  /** Last connection or protocol error shown to the user. */
  lastError = $state<string | null>(null);

  #byName = new Map<string, StreamState>();
  #socket: WebSocket | null = null;
  #reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  #frameHandle: number | null = null;
  #stopped = false;

  /**
   * Opens the WebSocket and starts consuming frames.
   *
   * @param url - WebSocket URL; defaults to the resolved server URL.
   */
  connect(url: string = resolveSocketUrl()): void {
    this.#stopped = false;
    this.status = "connecting";

    let socket: WebSocket;
    try {
      socket = new WebSocket(url);
    } catch {
      this.lastError = "Unable to open a WebSocket connection.";
      this.#scheduleReconnect(url);
      return;
    }
    this.#socket = socket;

    socket.onopen = () => {
      this.status = "open";
      this.lastError = null;
    };
    socket.onmessage = (event) => this.#handleMessage(event.data);
    socket.onerror = () => {
      this.lastError = "WebSocket error - is the MoBI-View server running?";
    };
    socket.onclose = () => {
      this.status = "closed";
      this.discovering = false;
      this.#scheduleReconnect(url);
    };
  }

  /** Closes the socket and cancels pending timers. */
  disconnect(): void {
    this.#stopped = true;
    if (this.#reconnectTimer !== null) clearTimeout(this.#reconnectTimer);
    if (this.#frameHandle !== null) cancelAnimationFrame(this.#frameHandle);
    this.#reconnectTimer = null;
    this.#frameHandle = null;
    this.#socket?.close();
    this.#socket = null;
  }

  /** Asks the server to resolve any LSL streams that appeared since startup. */
  discover(): void {
    if (this.#socket?.readyState !== WebSocket.OPEN) return;
    this.discovering = true;
    this.#socket.send(JSON.stringify({ command: "discover" }));
  }

  /** Clears all buffered history while keeping the connection open. */
  clearHistory(): void {
    for (const state of this.#byName.values()) {
      state.timestamps.length = 0;
      for (const column of state.values) column.length = 0;
      state.markers.length = 0;
      state.sampleCount = 0;
      state.firstTimestamp = 0;
    }
    this.#requestRender();
  }

  #scheduleReconnect(url: string): void {
    if (this.#stopped || this.#reconnectTimer !== null) return;
    this.#reconnectTimer = setTimeout(() => {
      this.#reconnectTimer = null;
      this.connect(url);
    }, RECONNECT_DELAY_MS);
  }

  #handleMessage(raw: unknown): void {
    if (typeof raw !== "string") return;

    let payload: unknown;
    try {
      payload = JSON.parse(raw);
    } catch {
      return;
    }
    if (typeof payload !== "object" || payload === null) return;

    if ((payload as { type?: string }).type === "discover_result") {
      this.discovering = false;
      return;
    }

    const frame = payload as IncomingFrame;
    if (!Array.isArray(frame.streams)) return;
    this.#applyFrame(frame);
  }

  #applyFrame(frame: IncomingFrame): void {
    let structureChanged = false;

    for (const incoming of frame.streams) {
      if (!incoming?.stream_name || !Array.isArray(incoming.samples)) continue;

      let state = this.#byName.get(incoming.stream_name);
      if (
        state === undefined ||
        state.labels.length !== (incoming.channel_labels?.length ?? 0)
      ) {
        state = createStreamState(incoming);
        this.#byName.set(incoming.stream_name, state);
        structureChanged = true;
      }
      appendSamples(state, incoming);
    }

    if (structureChanged) {
      // EEG first, then other numeric streams, with marker streams last.
      this.streams = [...this.#byName.values()].sort((a, b) => {
        const rank = (s: StreamState) => (s.isEeg ? 0 : s.isMarker ? 2 : 1);
        return rank(a) - rank(b) || a.name.localeCompare(b.name);
      });
    }
    this.#requestRender();
  }

  #requestRender(): void {
    if (this.#frameHandle !== null || this.#stopped) return;
    this.#frameHandle = requestAnimationFrame(() => {
      this.#frameHandle = null;
      this.revision += 1;
    });
  }
}
