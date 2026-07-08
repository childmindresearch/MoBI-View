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

/** A single stream's latest sample within a data frame. */
export interface StreamData {
  stream_name: string;
  data: number[];
  channel_labels: string[];
}

/** Periodic data frame broadcast to every connected client. */
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
  return (
    (message as DiscoverResultMessage).type === undefined &&
    Array.isArray((message as DataFrameMessage).streams)
  );
}

/**
 * Parses a raw WebSocket payload into a typed server message.
 *
 * @param raw - The raw string payload from a WebSocket `message` event.
 * @returns The typed message, or null when the payload is unrecognised.
 */
export function parseServerMessage(raw: string): ServerMessage | null {
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    return null;
  }

  if (typeof parsed !== "object" || parsed === null) {
    return null;
  }

  const candidate = parsed as Record<string, unknown>;

  if (
    candidate.type === "discover_result" &&
    Array.isArray(candidate.streams)
  ) {
    return { type: "discover_result", streams: candidate.streams as string[] };
  }

  if (candidate.type === undefined && Array.isArray(candidate.streams)) {
    return { streams: candidate.streams as StreamData[] };
  }

  return null;
}
