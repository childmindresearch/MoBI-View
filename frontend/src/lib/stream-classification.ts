/**
 * Pure helpers that classify streams as EEG, numeric, or marker and order
 * them so every view shows streams in the same sequence.
 *
 * Marker classification is sticky: once a stream is a marker it stays one
 * until its channel layout or `stream_type` changes. A missing `stream_type`
 * is distinct from any declared type, including an empty string.
 */

import type { StreamData } from "$lib/protocol";

/** Display category for a stream. */
export type StreamCategory = "eeg" | "numeric" | "marker";

/** Classification state for one stream, kept between batches. */
export interface StreamClassification {
  category: StreamCategory;
  streamType: string | undefined;
  channelLabels: string[];
}

/** Classification state per stream, keyed by stream name. */
export type StreamClassifications = Record<string, StreamClassification>;

const CATEGORY_RANK: Record<StreamCategory, number> = {
  eeg: 0,
  numeric: 1,
  marker: 2,
};

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
 * Checks for a case-insensitive exact `EEG` stream type.
 *
 * @param streamType - The stream's declared type, if any.
 * @returns True when the type is `EEG` in any case.
 */
export function isEegType(streamType: string | undefined): boolean {
  return streamType?.toLowerCase() === "eeg";
}

/**
 * Checks for a case-insensitive exact `Markers` stream type.
 *
 * @param streamType - The stream's declared type, if any.
 * @returns True when the type is `Markers` in any case.
 */
export function isMarkersType(streamType: string | undefined): boolean {
  return streamType?.toLowerCase() === "markers";
}

/**
 * Classifies a stream from its latest batch and prior state.
 *
 * Marker wins over EEG: a `Markers` type or any string sample makes the
 * whole stream a marker. A prior marker classification is kept while the
 * channel layout and `stream_type` are unchanged, even across empty or
 * all-numeric batches.
 *
 * @param previous - The stream's prior classification, if any.
 * @param stream - The incoming batch.
 * @returns The stream's new classification.
 */
export function classifyStream(
  previous: StreamClassification | undefined,
  stream: StreamData,
): StreamClassification {
  const streamType = stream.stream_type;
  const channelLabels = stream.channel_labels;
  const stickyMarker =
    previous !== undefined &&
    previous.category === "marker" &&
    previous.streamType === streamType &&
    sameLabels(previous.channelLabels, channelLabels);
  const hasString = stream.samples.some((row) =>
    row.some((value) => typeof value === "string"),
  );

  let category: StreamCategory;
  if (stickyMarker || isMarkersType(streamType) || hasString) {
    category = "marker";
  } else if (isEegType(streamType)) {
    category = "eeg";
  } else {
    category = "numeric";
  }
  return { category, streamType, channelLabels: [...channelLabels] };
}

/**
 * Applies a frame's batches to classification state without mutating it.
 *
 * Only own keys are read and written, so names like `constructor` and
 * `__proto__` behave as ordinary streams. Repeated names accumulate.
 *
 * @param current - Existing classifications.
 * @param streams - Batches from one data frame.
 * @returns A new classification record.
 */
export function updateClassifications(
  current: StreamClassifications,
  streams: StreamData[],
): StreamClassifications {
  const next: StreamClassifications = {};
  for (const name of Object.keys(current)) {
    defineOwn(next, name, current[name]);
  }
  for (const stream of streams) {
    const name = stream.stream_name;
    const previous = hasOwn(next, name) ? next[name] : undefined;
    defineOwn(next, name, classifyStream(previous, stream));
  }
  return next;
}

/**
 * Defines an own classification key, keeping names like "__proto__" ordinary.
 *
 * @param record - The destination classification record.
 * @param key - The stream name to define.
 * @param value - The classification stored under the key.
 */
function defineOwn(
  record: StreamClassifications,
  key: string,
  value: StreamClassification,
): void {
  Object.defineProperty(record, key, {
    value,
    enumerable: true,
    writable: true,
    configurable: true,
  });
}

/**
 * Compares two streams: EEG first, other numeric next, markers last, then
 * by name using code-unit order so results don't depend on locale.
 *
 * @param a - First stream's name and category.
 * @param b - Second stream's name and category.
 * @returns Negative, zero, or positive, as for `Array.prototype.sort`.
 */
export function compareStreams(
  a: { name: string; category: StreamCategory },
  b: { name: string; category: StreamCategory },
): number {
  const rank = CATEGORY_RANK[a.category] - CATEGORY_RANK[b.category];
  if (rank !== 0) {
    return rank;
  }
  if (a.name === b.name) {
    return 0;
  }
  return a.name < b.name ? -1 : 1;
}

/**
 * Orders the classified streams' names for display.
 *
 * @param classifications - Classifications keyed by stream name (own keys only).
 * @returns Stream names sorted by `compareStreams`.
 */
export function orderStreamNames(
  classifications: StreamClassifications,
): string[] {
  return Object.keys(classifications)
    .map((name) => ({ name, category: classifications[name].category }))
    .sort(compareStreams)
    .map((entry) => entry.name);
}
