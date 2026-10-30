/**
 * Svelte stores aggregating live data received over the WebSocket connection.
 *
 * `streamSamples` keeps the most recent batch for every stream seen in a data
 * frame; `discoveredStreams` holds the stream names returned by the most recent
 * discovery request; `streamHistory` keeps a bounded, column-oriented rolling
 * window of the newest `MAX_POINTS` rows per stream. All are populated by
 * subscribing to a connection store's decoded messages.
 */

import { writable, type Readable } from "svelte/store";

import {
  isDataFrame,
  isDiscoverResult,
  type SampleValue,
  type StreamData,
} from "$lib/protocol";
import { websocketStore, type WebSocketStore } from "$lib/stores/websocket";

/** Latest batch of samples for each stream, keyed by stream name. */
export type StreamSamples = Record<string, StreamData>;

/** Maximum rows retained per stream in `streamHistory`. */
export const MAX_POINTS = 1250;

/** A string sample value recorded as a marker event. */
export interface StreamMarker {
  timestamp: number;
  /** Index of the channel that carried the string. */
  channel: number;
  text: string;
  /** Cumulative row index (0-based, counted like `sampleCount`). */
  sampleIndex: number;
}

/**
 * Bounded rolling history for one stream, stored column-oriented.
 *
 * Arrays are reused and mutated in place across updates; each update emits a
 * new history object so store subscribers are notified.
 */
export interface StreamHistory {
  channel_labels: string[];
  /** Retained row timestamps, oldest first; at most `MAX_POINTS` entries. */
  timestamps: number[];
  /** One numeric column per channel; strings and non-finite values are NaN. */
  values: number[][];
  /** Raw final row of the most recent non-empty batch; empty initially. */
  latest: SampleValue[];
  /** String values whose rows are still retained, oldest first. */
  markers: StreamMarker[];
  /** Total rows received for the stream, independent of trimming/resets. */
  sampleCount: number;
}

/** Rolling history per stream, keyed by stream name. */
export type StreamHistories = Record<string, StreamHistory>;

/** Live-data stores bound to a WebSocket connection store. */
export interface StreamStores {
  streamSamples: Readable<StreamSamples>;
  streamHistory: Readable<StreamHistories>;
  discoveredStreams: Readable<string[]>;
  stop: () => void;
}

function sameLabels(a: string[], b: string[]): boolean {
  return a.length === b.length && a.every((label, i) => label === b[i]);
}

/**
 * Appends a batch into a stream's history, trimming each array at most once.
 * A changed channel layout discards retained rows but keeps `sampleCount`.
 */
function appendBatch(
  previous: StreamHistory | undefined,
  stream: StreamData,
): StreamHistory {
  const labels = stream.channel_labels;
  const history: StreamHistory =
    previous !== undefined && sameLabels(previous.channel_labels, labels)
      ? { ...previous }
      : {
          channel_labels: [...labels],
          timestamps: [],
          values: labels.map(() => []),
          latest: [],
          markers: [],
          sampleCount: previous?.sampleCount ?? 0,
        };

  const { samples, timestamps } = stream;
  for (let row = 0; row < samples.length; row++) {
    const timestamp = timestamps[row];
    history.timestamps.push(timestamp);
    samples[row].forEach((value, channel) => {
      if (typeof value === "string") {
        history.values[channel].push(NaN);
        history.markers.push({
          timestamp,
          channel,
          text: value,
          sampleIndex: history.sampleCount + row,
        });
      } else {
        history.values[channel].push(Number.isFinite(value) ? value : NaN);
      }
    });
  }
  history.sampleCount += samples.length;
  if (samples.length > 0) {
    history.latest = [...samples[samples.length - 1]];
  }

  const overflow = history.timestamps.length - MAX_POINTS;
  if (overflow > 0) {
    history.timestamps.splice(0, overflow);
    for (const column of history.values) {
      column.splice(0, overflow);
    }
    const firstRetained = history.sampleCount - MAX_POINTS;
    const firstKept = history.markers.findIndex(
      (marker) => marker.sampleIndex >= firstRetained,
    );
    history.markers.splice(
      0,
      firstKept === -1 ? history.markers.length : firstKept,
    );
  }
  return history;
}

/**
 * Creates live-data stores bound to a WebSocket connection store.
 *
 * @param connection - The connection store to subscribe to.
 * @returns The sample, history, and discovery stores plus an unsubscribe function.
 */
export function createStreamStores(
  connection: WebSocketStore = websocketStore,
): StreamStores {
  const streamSamples = writable<StreamSamples>({});
  const streamHistory = writable<StreamHistories>({});
  const discoveredStreams = writable<string[]>([]);

  const stop = connection.onMessage((message) => {
    if (isDiscoverResult(message)) {
      discoveredStreams.set(message.streams);
    } else if (isDataFrame(message)) {
      streamSamples.update((current) => {
        const next = { ...current };
        for (const stream of message.streams) {
          next[stream.stream_name] = stream;
        }
        return next;
      });
      streamHistory.update((current) => {
        const next = { ...current };
        for (const stream of message.streams) {
          const name = stream.stream_name;
          // Read `next` so repeated names in one frame accumulate, and only own
          // keys so names like "constructor" don't resolve to prototype values.
          const previous = Object.prototype.hasOwnProperty.call(next, name)
            ? next[name]
            : undefined;
          // Define rather than assign so "__proto__" stays an own data key.
          Object.defineProperty(next, name, {
            value: appendBatch(previous, stream),
            enumerable: true,
            writable: true,
            configurable: true,
          });
        }
        return next;
      });
    }
  });

  return { streamSamples, streamHistory, discoveredStreams, stop };
}

const stores = createStreamStores();

/** Latest batch per active stream, keyed by stream name. */
export const streamSamples = stores.streamSamples;

/** Bounded rolling history per stream, keyed by stream name. */
export const streamHistory = stores.streamHistory;

/** Stream names returned by the most recent discovery request. */
export const discoveredStreams = stores.discoveredStreams;

/** Removes the application-wide store's WebSocket message subscription. */
export const stopStreamStores = stores.stop;
