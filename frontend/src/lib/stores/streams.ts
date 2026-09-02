/**
 * Svelte stores aggregating live data received over the WebSocket connection.
 *
 * `streamSamples` keeps the most recent sample for every stream seen in a data
 * frame; `discoveredStreams` holds the stream names returned by the most recent
 * discovery request. Both are populated by subscribing to a connection store's
 * decoded messages.
 */

import { writable, type Readable } from "svelte/store";

import { isDataFrame, isDiscoverResult, type StreamData } from "$lib/protocol";
import { websocketStore, type WebSocketStore } from "$lib/stores/websocket";

/** Latest sample for each stream, keyed by stream name. */
export type StreamSamples = Record<string, StreamData>;

/** Live-data stores bound to a WebSocket connection store. */
export interface StreamStores {
  streamSamples: Readable<StreamSamples>;
  discoveredStreams: Readable<string[]>;
  stop: () => void;
}

/**
 * Creates live-data stores bound to a WebSocket connection store.
 *
 * @param connection - The connection store to subscribe to.
 * @returns The sample and discovery stores plus an unsubscribe function.
 */
export function createStreamStores(
  connection: WebSocketStore = websocketStore,
): StreamStores {
  const streamSamples = writable<StreamSamples>({});
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
    }
  });

  return { streamSamples, discoveredStreams, stop };
}

const stores = createStreamStores();

/** Latest sample per active stream, keyed by stream name. */
export const streamSamples = stores.streamSamples;

/** Stream names returned by the most recent discovery request. */
export const discoveredStreams = stores.discoveredStreams;

/** Removes the application-wide store's WebSocket message subscription. */
export const stopStreamStores = stores.stop;
