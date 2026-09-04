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

  it("records the latest sample for each stream in a data frame", () => {
    const connection = createFakeConnection();
    const { streamSamples } = createStreamStores(connection);

    connection.emit(
      JSON.stringify({
        streams: [
          { stream_name: "EEG", data: [1, 2], channel_labels: ["a", "b"] },
          { stream_name: "Gaze", data: [3], channel_labels: ["x"] },
        ],
      }),
    );

    expect(get(streamSamples)).toEqual({
      EEG: { stream_name: "EEG", data: [1, 2], channel_labels: ["a", "b"] },
      Gaze: { stream_name: "Gaze", data: [3], channel_labels: ["x"] },
    });
  });

  it("overwrites a stream with its most recent sample", () => {
    const connection = createFakeConnection();
    const { streamSamples } = createStreamStores(connection);

    connection.emit(
      JSON.stringify({
        streams: [{ stream_name: "EEG", data: [1], channel_labels: ["a"] }],
      }),
    );
    connection.emit(
      JSON.stringify({
        streams: [{ stream_name: "EEG", data: [9], channel_labels: ["a"] }],
      }),
    );

    expect(get(streamSamples)).toEqual({
      EEG: { stream_name: "EEG", data: [9], channel_labels: ["a"] },
    });
  });

  it("stops receiving data after stop is called", () => {
    const connection = createFakeConnection();
    const { streamSamples, stop } = createStreamStores(connection);

    connection.emit(
      JSON.stringify({
        streams: [{ stream_name: "EEG", data: [1], channel_labels: ["a"] }],
      }),
    );
    stop();
    connection.emit(
      JSON.stringify({
        streams: [{ stream_name: "EEG", data: [9], channel_labels: ["a"] }],
      }),
    );

    expect(get(streamSamples)).toEqual({
      EEG: { stream_name: "EEG", data: [1], channel_labels: ["a"] },
    });
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
