/**
 * Live data aggregated from a WebSocket connection store's decoded messages.
 *
 * `streamHistory` is a plain, non-reactive `Map` holding a bounded rolling
 * window per stream (numeric rows or marker events); it is updated immediately
 * as frames arrive and keeps its identity for the store's lifetime.
 * `revision`, `streamSamples`, and `orderedStreams` are published at most once
 * per animation frame (synchronously when `requestAnimationFrame` is
 * unavailable); consumers read `streamHistory` when `revision` changes.
 * `streamSamples` keeps the latest batch for every stream seen during the
 * store's lifetime; `orderedStreams` lists those batches in display order.
 * `discoveredStreams` holds the names from the most recent discovery request
 * and is published immediately.
 */

import { readonly, writable, type Readable } from "svelte/store";

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

/**
 * Rolling history per stream, keyed by stream name. Mutated in place; read it
 * when `revision` changes.
 */
export type StreamHistories = ReadonlyMap<string, StreamHistory>;

/** Live-data stores bound to a WebSocket connection store. */
export interface StreamStores {
  streamSamples: Readable<StreamSamples>;
  streamHistory: StreamHistories;
  revision: Readable<number>;
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
 * Adds a batch to a stream's history in place, trimming overflow once.
 *
 * `reset` (a layout, type, or category change) discards retained buffers and
 * `latest`, so a numeric-to-marker switch keeps no numeric rows and stores
 * the whole current batch as events.
 *
 * @param history - The stream's history, mutated in place.
 * @param incomingStream - The incoming batch for the stream.
 * @param category - The stream's classification after this batch.
 * @param reset - Whether retained buffers must start fresh.
 */
function appendBatch(
  history: StreamHistory,
  incomingStream: StreamData,
  category: StreamCategory,
  reset: boolean,
): void {
  if (reset) {
    const labels = incomingStream.channel_labels;
    history.category = category;
    history.channel_labels = [...labels];
    history.timestamps = [];
    history.values = emptyValues(category, labels);
    history.latest = [];
    history.markers = [];
  }

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
}

/**
 * Creates live-data stores bound to a WebSocket connection store.
 *
 * Incoming data updates `streamHistory` and internal state immediately;
 * `revision`, `streamSamples`, and `orderedStreams` publish together at most
 * once per animation frame, or synchronously without `requestAnimationFrame`.
 *
 * @param connection - The connection store to subscribe to.
 * @returns The history map, revision, sample, ordering, and discovery stores,
 *   plus `clearHistory` and a stop function.
 */
export function createStreamStores(
  connection: WebSocketStore = websocketStore,
): StreamStores {
  const streamHistory = new Map<string, StreamHistory>();
  const revision = writable(0);
  const streamSamples = writable<StreamSamples>({});
  const orderedStreams = writable<StreamData[]>([]);
  const discoveredStreams = writable<string[]>([]);
  // Canonical pending state, separate from the published snapshots; it must
  // survive clearHistory so sticky marker streams stay markers.
  const latestSamples = new Map<string, StreamData>();
  const classifications: StreamClassifications = {};

  let revisionValue = 0;
  let samplesChanged = false;
  let publishPending = false;
  let publishing = false;
  let frameId: number | null = null;
  let stopped = false;

  /**
   * Publishes snapshots and bumps `revision`, rebuilding samples if changed.
   *
   * Every snapshot is captured before any subscriber runs, so input delivered
   * by a subscriber mid-publication cannot mix into this publication; it marks
   * state changed again and is published by the next one.
   */
  function publish(): void {
    publishPending = false;
    let snapshot: { samples: StreamSamples; ordered: StreamData[] } | null =
      null;
    if (samplesChanged) {
      samplesChanged = false;
      const samples: StreamSamples = {};
      for (const [name, stream] of latestSamples) {
        defineOwn(samples, name, stream);
      }
      const ordered = orderStreamNames(classifications).map(
        (name) => samples[name],
      );
      snapshot = { samples, ordered };
    }
    revisionValue += 1;
    const nextRevision = revisionValue;
    if (snapshot !== null) {
      streamSamples.set(snapshot.samples);
      orderedStreams.set(snapshot.ordered);
    }
    revision.set(nextRevision);
  }

  /**
   * Runs the pending publication. Requests made by subscribers while
   * publishing go to the next frame, or run in order right after this one
   * when publishing synchronously, so publications never nest.
   */
  function flush(): void {
    frameId = null;
    if (stopped || publishing) {
      return;
    }
    publishing = true;
    try {
      while (publishPending && !stopped && frameId === null) {
        publish();
      }
    } finally {
      publishing = false;
    }
  }

  /** Requests one publication on the next animation frame. */
  function schedulePublish(): void {
    if (stopped) {
      return;
    }
    publishPending = true;
    if (frameId !== null) {
      return;
    }
    // Looked up per call so environments (and tests) can provide it later.
    const requestFrame = globalThis.requestAnimationFrame;
    if (typeof requestFrame === "function") {
      frameId = requestFrame(flush);
    } else if (!publishing) {
      flush();
    }
  }

  const unsubscribe = connection.onMessage((message) => {
    if (isDiscoverResult(message)) {
      discoveredStreams.set(message.streams);
    } else if (isDataFrame(message)) {
      for (const stream of message.streams) {
        const name = stream.stream_name;
        // Own keys only, so names like "constructor" don't resolve to prototypes.
        const previous = Object.prototype.hasOwnProperty.call(
          classifications,
          name,
        )
          ? classifications[name]
          : undefined;
        const current = classifyStream(previous, stream);
        const reset =
          previous === undefined ||
          previous.category !== current.category ||
          previous.streamType !== current.streamType ||
          !sameLabels(previous.channelLabels, current.channelLabels);
        defineOwn(classifications, name, current);
        latestSamples.set(name, stream);
        let history = streamHistory.get(name);
        if (history === undefined) {
          history = {
            category: current.category,
            channel_labels: [],
            timestamps: [],
            values: [],
            latest: [],
            markers: [],
            sampleCount: 0,
          };
          streamHistory.set(name, history);
        }
        appendBatch(history, stream, current.category, reset);
      }
      samplesChanged = true;
      schedulePublish();
    }
  });

  /**
   * Clears retained timestamps, values, and markers immediately while
   * preserving stream membership, latest samples, sample counts,
   * classifications, and discovery; notifies through the frame queue.
   */
  function clearHistory(): void {
    for (const history of streamHistory.values()) {
      history.timestamps.length = 0;
      for (const column of history.values) {
        column.length = 0;
      }
      history.markers.length = 0;
    }
    schedulePublish();
  }

  /**
   * Cancels any pending publication and unsubscribes; accepted history stays.
   */
  function stop(): void {
    stopped = true;
    publishPending = false;
    if (frameId !== null) {
      globalThis.cancelAnimationFrame?.(frameId);
      frameId = null;
    }
    unsubscribe();
  }

  return {
    streamSamples: readonly(streamSamples),
    streamHistory,
    revision: readonly(revision),
    orderedStreams: readonly(orderedStreams),
    discoveredStreams: readonly(discoveredStreams),
    clearHistory,
    stop,
  };
}

const stores = createStreamStores();

/** Latest batch per stream seen since load, keyed by stream name. */
export const streamSamples = stores.streamSamples;

/** Bounded rolling history per stream, keyed by stream name; non-reactive. */
export const streamHistory = stores.streamHistory;

/** Increments once per publication; read `streamHistory` when it changes. */
export const revision = stores.revision;

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
