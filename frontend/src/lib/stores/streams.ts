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

/**
 * Text from a string sample, kept so it can be drawn as a marker.
 * `sampleIndex` is the sample's zero-based cumulative row number, so markers
 * leave the history with their rows rather than by timestamp.
 */
export interface StreamMarker {
  timestamp: number;
  channel: number;
  text: string;
  sampleIndex: number;
}

/**
 * Rolling history for one stream, holding at most `MAX_POINTS` rows.
 *
 * `values` has one column per channel, aligned with `timestamps`. Strings and
 * non-finite numbers show up as NaN gaps; string text is kept in `markers`.
 * `latest` is the raw last row of the most recent non-empty batch (empty at
 * first). `sampleCount` keeps counting through trimming and layout changes.
 */
export interface StreamHistory {
  channel_labels: string[];
  timestamps: number[];
  values: number[][];
  latest: SampleValue[];
  markers: StreamMarker[];
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
 * Adds a batch to a stream's history, trimming excess rows once per batch.
 *
 * A changed channel layout starts fresh arrays and clears `latest` and
 * `markers`, even for an empty batch. Otherwise the existing arrays are
 * mutated in place; a new history object is still returned so subscribers
 * are notified.
 *
 * @param previous - The stream's current history, if any.
 * @param stream - The incoming batch for the stream.
 * @returns A new history object reflecting the appended batch.
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
