/**
 * Svelte stores aggregating live data received over the WebSocket connection.
 *
 * `streamSamples` keeps the most recent batch for every stream seen in a data
 * frame during the store's lifetime; streams absent from later frames,
 * reconnects, and `clearHistory` never remove entries. `orderedStreams` lists
 * those batches in display order;
 * `discoveredStreams` holds the names from the most recent discovery request;
 * `streamHistory` keeps a bounded rolling window per stream: numeric rows for
 * numeric streams, marker events for marker streams. All are populated by
 * subscribing to a connection store's decoded messages.
 */

import { get, writable, type Readable } from "svelte/store";

import {
  isDataFrame,
  isDiscoverResult,
  type SampleValue,
  type StreamData,
} from "$lib/protocol";
import {
  classifyStream,
  orderStreamNames,
  type StreamCategory,
  type StreamClassifications,
} from "$lib/stream-classification";
import { websocketStore, type WebSocketStore } from "$lib/stores/websocket";

/** Latest batch of samples for each stream, keyed by stream name. */
export type StreamSamples = Record<string, StreamData>;

/** Maximum rows retained per numeric stream in `streamHistory`. */
export const MAX_POINTS = 1250;

/** Maximum marker events retained per marker stream in `streamHistory`. */
export const MAX_MARKERS = 250;

/**
 * One marker value, kept as received (number or string) with its row time.
 *
 * `channelIndex` is the zero-based originating channel; its label is
 * `history.channel_labels[channelIndex]`. Layout changes reset markers, so
 * retained indices always refer to the current labels.
 */
export interface StreamMarker {
  timestamp: number;
  value: SampleValue;
  channelIndex: number;
}

/**
 * Rolling history for one stream.
 *
 * Numeric (`eeg`/`numeric`) streams keep up to `MAX_POINTS` rows in
 * `timestamps` and one aligned `values` column per channel; `markers` stays
 * empty. Marker streams keep up to `MAX_MARKERS` events in `markers`, one per
 * channel per row, with `timestamps` and `values` empty. `latest` is the raw
 * last row of the most recent non-empty batch. `sampleCount` counts rows
 * cumulatively through trimming, resets, and clearing.
 */
export interface StreamHistory {
  category: StreamCategory;
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
  orderedStreams: Readable<StreamData[]>;
  discoveredStreams: Readable<string[]>;
  clearHistory: () => void;
  stop: () => void;
}

/**
 * Compares channel layouts to decide whether prior stream state can carry over.
 *
 * @param a - First channel-label list.
 * @param b - Second channel-label list.
 * @returns Whether the channel layouts are unchanged.
 */
function sameLabels(a: string[], b: string[]): boolean {
  return a.length === b.length && a.every((label, i) => label === b[i]);
}

/**
 * Checks own properties without matching inherited prototype keys.
 * Stream names like `__proto__` and `constructor` must remain ordinary keys.
 *
 * @param record - Record to inspect.
 * @param key - Key to check.
 * @returns Whether `key` is an own property, not inherited from the prototype.
 */
function hasOwn(record: object, key: string): boolean {
  return Object.prototype.hasOwnProperty.call(record, key);
}

/**
 * Defines an own data key, so names like "__proto__" don't touch the prototype.
 *
 * @param record - The destination record.
 * @param key - The stream name to define.
 * @param value - The value stored under the key.
 */
function defineOwn<T>(record: Record<string, T>, key: string, value: T): void {
  Object.defineProperty(record, key, {
    value,
    enumerable: true,
    writable: true,
    configurable: true,
  });
}

/**
 * Creates numeric columns for non-marker streams; markers need no numeric buffers.
 *
 * @param category - Classification determining whether numeric columns apply.
 * @param labels - Channel labels that determine the numeric column count.
 * @returns Empty numeric columns, or no columns for marker streams.
 */
function emptyValues(category: StreamCategory, labels: string[]): number[][] {
  return category === "marker" ? [] : labels.map(() => []);
}

/**
 * Adds a batch to a stream's history, trimming overflow once per batch.
 *
 * `reset` (a layout, type, or category change) discards retained buffers and
 * `latest`, so a numeric-to-marker switch keeps no numeric rows and stores
 * the whole current batch as events. Otherwise arrays are mutated in place;
 * a new history object is still returned so subscribers are notified.
 *
 * @param historicalStream - The stream's existing history, if any.
 * @param incomingStream - The incoming batch for the stream.
 * @param category - The stream's classification after this batch.
 * @param reset - Whether retained buffers must start fresh.
 * @returns A new history object reflecting the appended batch.
 */
function appendBatch(
  historicalStream: StreamHistory | undefined,
  incomingStream: StreamData,
  category: StreamCategory,
  reset: boolean,
): StreamHistory {
  const labels = incomingStream.channel_labels;
  const history: StreamHistory =
    historicalStream !== undefined && !reset
      ? { ...historicalStream }
      : {
          category,
          channel_labels: [...labels],
          timestamps: [],
          values: emptyValues(category, labels),
          latest: [],
          markers: [],
          sampleCount: historicalStream?.sampleCount ?? 0,
        };

  const { samples, timestamps } = incomingStream;
  if (category === "marker") {
    samples.forEach((row, i) => {
      row.forEach((value, channelIndex) => {
        history.markers.push({ timestamp: timestamps[i], value, channelIndex });
      });
    });
    // Counts events, so the oldest retained event may start mid-row.
    const overflow = history.markers.length - MAX_MARKERS;
    if (overflow > 0) {
      history.markers.splice(0, overflow);
    }
  } else {
    samples.forEach((row, i) => {
      history.timestamps.push(timestamps[i]);
      row.forEach((value, channel) => {
        // Numeric streams carry no strings; the type guard only narrows.
        history.values[channel].push(
          typeof value === "number" && Number.isFinite(value) ? value : NaN,
        );
      });
    });
    const overflow = history.timestamps.length - MAX_POINTS;
    if (overflow > 0) {
      history.timestamps.splice(0, overflow);
      for (const column of history.values) {
        column.splice(0, overflow);
      }
    }
  }

  history.sampleCount += samples.length;
  if (samples.length > 0) {
    history.latest = [...samples[samples.length - 1]];
  }
  return history;
}

/**
 * Creates live-data stores bound to a WebSocket connection store.
 *
 * @param connection - The connection store to subscribe to.
 * @returns The sample, history, ordering, and discovery stores, plus
 *   `clearHistory` and an unsubscribe function.
 */
export function createStreamStores(
  connection: WebSocketStore = websocketStore,
): StreamStores {
  const streamSamples = writable<StreamSamples>({});
  const streamHistory = writable<StreamHistories>({});
  const orderedStreams = writable<StreamData[]>([]);
  const discoveredStreams = writable<string[]>([]);
  // Plain state rather than a store: only used to classify and order, and it
  // must survive clearHistory so sticky marker streams stay markers.
  let classifications: StreamClassifications = {};

  const stop = connection.onMessage((message) => {
    if (isDiscoverResult(message)) {
      discoveredStreams.set(message.streams);
    } else if (isDataFrame(message)) {
      const samples = { ...get(streamSamples) };
      const histories = { ...get(streamHistory) };
      const nextClassifications = { ...classifications };
      for (const stream of message.streams) {
        const name = stream.stream_name;
        // Read the copies so repeated names in one frame accumulate, and only
        // own keys so names like "constructor" don't resolve to prototypes.
        const previous = hasOwn(nextClassifications, name)
          ? nextClassifications[name]
          : undefined;
        const historicalStream = hasOwn(histories, name)
          ? histories[name]
          : undefined;
        const current = classifyStream(previous, stream);
        const reset =
          previous === undefined ||
          previous.category !== current.category ||
          previous.streamType !== current.streamType ||
          !sameLabels(previous.channelLabels, current.channelLabels);
        defineOwn(nextClassifications, name, current);
        defineOwn(samples, name, stream);
        defineOwn(
          histories,
          name,
          appendBatch(historicalStream, stream, current.category, reset),
        );
      }
      classifications = nextClassifications;
      streamSamples.set(samples);
      streamHistory.set(histories);
      orderedStreams.set(
        orderStreamNames(classifications).map((name) => samples[name]),
      );
    }
  });

  /**
   * Clears retained timestamps, values, and markers while preserving stream
   * membership, latest samples, sample counts, classifications, and discovery.
   */
  function clearHistory(): void {
    streamHistory.update((current) => {
      const next: StreamHistories = {};
      for (const name of Object.keys(current)) {
        const history = current[name];
        defineOwn<StreamHistory>(next, name, {
          ...history,
          timestamps: [],
          values: history.values.map(() => []),
          markers: [],
        });
      }
      return next;
    });
  }

  return {
    streamSamples,
    streamHistory,
    orderedStreams,
    discoveredStreams,
    clearHistory,
    stop,
  };
}

const stores = createStreamStores();

/** Latest batch per stream seen since load, keyed by stream name. */
export const streamSamples = stores.streamSamples;

/** Bounded rolling history per stream, keyed by stream name. */
export const streamHistory = stores.streamHistory;

/** Latest batches ordered for display, shared by every stream list. */
export const orderedStreams = stores.orderedStreams;

/**
 * Clears retained history while preserving latest samples and counts.
 *
 * @see StreamStores.clearHistory
 */
export const clearHistory = stores.clearHistory;

/** Stream names returned by the most recent discovery request. */
export const discoveredStreams = stores.discoveredStreams;

/** Removes the application-wide store's WebSocket message subscription. */
export const stopStreamStores = stores.stop;
