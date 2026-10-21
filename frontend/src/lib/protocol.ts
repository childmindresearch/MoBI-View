/**
 * WebSocket protocol definitions shared between the MoBI-View frontend and the
 * Python backend.
 *
 * The shapes here mirror the messages implemented in `MoBI_View.web.server`
 * (command handling) and `MoBI_View.web.broadcaster` (data frames). Keep this
 * file in sync with those modules whenever the wire format changes.
 */

/** Default WebSocket endpoint exposed by the Python backend. */
export const DEFAULT_WS_URL = "ws://localhost:8765";

/** Discovery request asking the backend to resolve LSL streams. */
export interface DiscoverCommand {
  command: "discover";
}

/** Any command the client may send to the server. */
export type ClientCommand = DiscoverCommand;

/** Result of a discovery request: names of newly discovered streams. */
export interface DiscoverResultMessage {
  type: "discover_result";
  streams: string[];
}

/** A numeric channel value or a string marker. */
export type SampleValue = number | string;

/** A stream's sample-major batch (one row per sample) and metadata. */
export interface StreamData {
  stream_name: string;
  samples: SampleValue[][];
  /** Source LSL clock times in seconds, one per sample row (not Unix time). */
  timestamps: number[];
  channel_labels: string[];
  stream_type?: string;
  channel_units?: string[];
}

/**
 * Periodic data frame broadcast to every connected client.
 *
 * Unlike `DiscoverResultMessage`, the backend (`Broadcaster.format_frame`)
 * sends this without a `type` field, so it is identified by shape rather
 * than by a tag.
 */
export interface DataFrameMessage {
  streams: StreamData[];
}

/** Any message the server may send to the client. */
export type ServerMessage = DiscoverResultMessage | DataFrameMessage;

/**
 * Builds the discovery command payload.
 *
 * @returns The `discover` command object ready to be serialised.
 */
export function discoverCommand(): DiscoverCommand {
  return { command: "discover" };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isStringArray(value: unknown): value is string[] {
  return (
    Array.isArray(value) &&
    value.every((item: unknown) => typeof item === "string")
  );
}

function isStreamData(value: unknown): value is StreamData {
  if (!isRecord(value) || !isStringArray(value.channel_labels)) {
    return false;
  }

  const channelCount = value.channel_labels.length;

  return (
    typeof value.stream_name === "string" &&
    Array.isArray(value.samples) &&
    value.samples.every(
      (sample: unknown) =>
        Array.isArray(sample) &&
        sample.length === channelCount &&
        sample.every(
          (channelValue: unknown) =>
            typeof channelValue === "number" ||
            typeof channelValue === "string",
        ),
    ) &&
    Array.isArray(value.timestamps) &&
    value.timestamps.length === value.samples.length &&
    value.timestamps.every(
      (timestamp: unknown) =>
        typeof timestamp === "number" && Number.isFinite(timestamp),
    ) &&
    (value.stream_type === undefined ||
      typeof value.stream_type === "string") &&
    (value.channel_units === undefined ||
      (isStringArray(value.channel_units) &&
        value.channel_units.length === channelCount))
  );
}

/**
 * Narrows a server message to a discovery result.
 *
 * @param message - The decoded server message.
 * @returns True when the message is a `discover_result`.
 */
export function isDiscoverResult(
  message: ServerMessage,
): message is DiscoverResultMessage {
  return (message as DiscoverResultMessage).type === "discover_result";
}

/**
 * Narrows a server message to a periodic data frame.
 *
 * @param message - The decoded server message.
 * @returns True when the message is a data frame.
 */
export function isDataFrame(
  message: ServerMessage,
): message is DataFrameMessage {
  // Data frames carry no `type` tag, so the absence of the discover_result
  // tag combined with a `streams` array identifies one.
  return (
    (message as DiscoverResultMessage).type !== "discover_result" &&
    Array.isArray((message as DataFrameMessage).streams)
  );
}

/**
 * Parses a raw WebSocket payload into a typed server message.
 *
 * @param raw - The raw string payload from a WebSocket `message` event.
 * @returns A `DiscoverResultMessage`, a `DataFrameMessage`, or null when
 *   `raw` is not valid JSON, is not an object, or matches neither shape.
 *   Invalid stream entries are omitted without discarding valid siblings.
 */
export function parseServerMessage(raw: string): ServerMessage | null {
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch (error) {
    if (!(error instanceof SyntaxError)) {
      throw error;
    }
    console.warn("Received invalid WebSocket JSON");
    return null;
  }

  if (!isRecord(parsed)) {
    console.warn("Received an invalid WebSocket server message");
    return null;
  }

  if (parsed.type === "discover_result" && isStringArray(parsed.streams)) {
    return { type: "discover_result", streams: parsed.streams };
  }

  if (parsed.type !== "discover_result" && Array.isArray(parsed.streams)) {
    const streams = parsed.streams.filter(isStreamData);
    const droppedEntries = parsed.streams.length - streams.length;
    if (droppedEntries > 0) {
      console.warn(
        "Dropped invalid stream entries from WebSocket data frame",
        droppedEntries,
      );
    }
    return { streams };
  }

  console.warn("Received an invalid WebSocket server message");
  return null;
}
