/** Unit tests for the live stream-data stores. */

import { describe, expect, it } from "vitest";
import { get } from "svelte/store";
import { writable } from "svelte/store";

import { parseServerMessage } from "$lib/protocol";
import type {
  ConnectionStatus,
  MessageHandler,
  WebSocketStore,
} from "$lib/stores/websocket";
import { createStreamStores } from "$lib/stores/streams";

/** Minimal connection-store double that lets a test emit server messages. */
function createFakeConnection(): WebSocketStore & {
  emit: (raw: string) => void;
} {
  let handler: MessageHandler | null = null;
  return {
    subscribe: writable<ConnectionStatus>("idle").subscribe,
    connect: () => {},
    disconnect: () => {},
    reconnect: () => {},
    sendDiscover: () => true,
    onMessage: (nextHandler: MessageHandler) => {
      handler = nextHandler;
      return () => {
        handler = null;
      };
    },
    emit: (raw) => {
      const message = parseServerMessage(raw);
      if (message !== null) {
        handler?.(message);
      }
    },
  };
}

describe("streamSamples", () => {
  it("starts empty", () => {
    const connection = createFakeConnection();
    const { streamSamples } = createStreamStores(connection);

    expect(get(streamSamples)).toEqual({});
  });

  it("records the latest batch for each stream in a data frame", () => {
    const connection = createFakeConnection();
    const { streamSamples } = createStreamStores(connection);
    const eegStream = {
      stream_name: "EEG",
      samples: [
        [1, 2],
        [3, 4],
      ],
      timestamps: [10, 10.004],
      channel_labels: ["a", "b"],
    };
    const gazeStream = {
      stream_name: "Gaze",
      samples: [[3]],
      timestamps: [10],
      channel_labels: ["x"],
    };

    connection.emit(
      JSON.stringify({
        streams: [eegStream, gazeStream],
      }),
    );

    expect(get(streamSamples)).toEqual({
      EEG: eegStream,
      Gaze: gazeStream,
    });
  });

  it("overwrites a stream with its most recent batch", () => {
    const connection = createFakeConnection();
    const { streamSamples } = createStreamStores(connection);
    const firstBatch = {
      stream_name: "EEG",
      samples: [[1]],
      timestamps: [10],
      channel_labels: ["a"],
    };
    const nextBatch = {
      ...firstBatch,
      samples: [[8], [9]],
      timestamps: [10.004, 10.008],
    };

    connection.emit(JSON.stringify({ streams: [firstBatch] }));
    connection.emit(JSON.stringify({ streams: [nextBatch] }));

    expect(get(streamSamples)).toEqual({ EEG: nextBatch });
  });

  it("stops receiving data after stop is called", () => {
    const connection = createFakeConnection();
    const { streamSamples, stop } = createStreamStores(connection);
    const firstBatch = {
      stream_name: "EEG",
      samples: [[1]],
      timestamps: [10],
      channel_labels: ["a"],
    };
    const nextBatch = {
      ...firstBatch,
      samples: [[9]],
      timestamps: [10.004],
    };

    connection.emit(JSON.stringify({ streams: [firstBatch] }));
    stop();
    connection.emit(JSON.stringify({ streams: [nextBatch] }));

    expect(get(streamSamples)).toEqual({ EEG: firstBatch });
  });
});

describe("discoveredStreams", () => {
  it("starts empty", () => {
    const connection = createFakeConnection();
    const { discoveredStreams } = createStreamStores(connection);

    expect(get(discoveredStreams)).toEqual([]);
  });

  it("records the names from a discover_result message", () => {
    const connection = createFakeConnection();
    const { discoveredStreams } = createStreamStores(connection);

    connection.emit(
      JSON.stringify({ type: "discover_result", streams: ["EEG", "Gaze"] }),
    );

    expect(get(discoveredStreams)).toEqual(["EEG", "Gaze"]);
  });

  it("does not populate samples from a discover_result", () => {
    const connection = createFakeConnection();
    const { streamSamples } = createStreamStores(connection);

    connection.emit(
      JSON.stringify({ type: "discover_result", streams: ["EEG"] }),
    );

    expect(get(streamSamples)).toEqual({});
  });
});
