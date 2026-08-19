/**
 * Shared types for the LSL stream data received over the WebSocket.
 */

/** A single channel value; marker streams carry strings, others numbers. */
export type SampleValue = number | string;

/** One stream entry inside a broadcast frame, as sent by the presenter. */
export type IncomingStream = {
  stream_name: string;
  stream_type?: string;
  channel_labels: string[];
  channel_units?: string[];
  timestamps: number[];
  samples: SampleValue[][];
};

/** Full broadcast frame pushed by the server on each poll tick. */
export type IncomingFrame = {
  streams: IncomingStream[];
};

/** A timestamped string marker event. */
export type MarkerEvent = {
  timestamp: number;
  value: string;
};

/** Connection state of the WebSocket link to the Python server. */
export type ConnectionStatus = "connecting" | "open" | "closed";

/**
 * Accumulated client-side history for one stream.
 *
 * `values` is column-oriented (one array per channel) so it can be handed to
 * uPlot without transposing on every frame.
 */
export type StreamState = {
  name: string;
  type: string;
  labels: string[];
  units: string[];
  timestamps: number[];
  values: number[][];
  latest: SampleValue[];
  markers: MarkerEvent[];
  sampleCount: number;
  firstTimestamp: number;
  lastTimestamp: number;
  isMarker: boolean;
  isEeg: boolean;
};