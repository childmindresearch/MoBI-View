/** Unit tests for the live stream-data stores. */

import { describe, expect, it, vi } from "vitest";
import { get } from "svelte/store";
import { writable } from "svelte/store";

import { parseServerMessage } from "$lib/protocol";
import type {
  ConnectionStatus,
  MessageHandler,
  WebSocketStore,
} from "$lib/stores/websocket";
import { MAX_POINTS, createStreamStores } from "$lib/stores/streams";

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

/** Builds a one-channel batch whose values and timestamps equal row numbers. */
function rows(start: number, count: number, name = "EEG") {
  const ids = Array.from({ length: count }, (_, i) => start + i);
  return {
    stream_name: name,
    samples: ids.map((id) => [id]),
    timestamps: ids,
    channel_labels: ["a"],
  };
}

describe("streamHistory", () => {
  it("starts empty", () => {
    const { streamHistory } = createStreamStores(createFakeConnection());

    expect(get(streamHistory)).toEqual({});
  });

  it("appends batches in order as aligned columns", () => {
    const connection = createFakeConnection();
    const { streamHistory } = createStreamStores(connection);
    const base = { stream_name: "EEG", channel_labels: ["a", "b"] };

    connection.emit(
      JSON.stringify({
        streams: [{ ...base, samples: [[1, 2]], timestamps: [10] }],
      }),
    );
    connection.emit(
      JSON.stringify({
        streams: [
          {
            ...base,
            samples: [
              [3, 4],
              [5, 6],
            ],
            timestamps: [11, 12],
          },
        ],
      }),
    );

    expect(get(streamHistory).EEG).toEqual({
      channel_labels: ["a", "b"],
      timestamps: [10, 11, 12],
      values: [
        [1, 3, 5],
        [2, 4, 6],
      ],
      latest: [5, 6],
      markers: [],
      sampleCount: 3,
    });
  });

  it("accumulates repeated stream names within a frame", () => {
    const connection = createFakeConnection();
    const { streamHistory } = createStreamStores(connection);

    connection.emit(JSON.stringify({ streams: [rows(0, 2), rows(2, 1)] }));
    let history = get(streamHistory).EEG;
    expect(history.timestamps).toEqual([0, 1, 2]);
    expect(history.sampleCount).toBe(3);

    connection.emit(JSON.stringify({ streams: [rows(3, 1), rows(4, 2)] }));
    history = get(streamHistory).EEG;
    expect(history.values).toEqual([[0, 1, 2, 3, 4, 5]]);
    expect(history.latest).toEqual([5]);
    expect(history.sampleCount).toBe(6);
  });

  it("handles stream names matching Object prototype properties", () => {
    const connection = createFakeConnection();
    const { streamHistory } = createStreamStores(connection);

    connection.emit(
      JSON.stringify({ streams: [rows(0, 1, "constructor"), rows(5, 1)] }),
    );

    const history = get(streamHistory);
    expect(history["constructor"]).toMatchObject({
      timestamps: [0],
      sampleCount: 1,
    });
    expect(history.EEG.timestamps).toEqual([5]);
  });

  it("accumulates a stream named __proto__ across frames", () => {
    const connection = createFakeConnection();
    const { streamHistory } = createStreamStores(connection);

    connection.emit(JSON.stringify({ streams: [rows(1, 1, "__proto__")] }));
    connection.emit(JSON.stringify({ streams: [rows(2, 1, "__proto__")] }));
    connection.emit(JSON.stringify({ streams: [rows(0, 1)] }));

    const history = get(streamHistory);
    expect(Object.keys(history)).toEqual(["__proto__", "EEG"]);
    const proto = Object.getOwnPropertyDescriptor(history, "__proto__")?.value;
    expect(proto).toMatchObject({ timestamps: [1, 2], sampleCount: 2 });
  });

  it("keeps streams independent", () => {
    const connection = createFakeConnection();
    const { streamHistory } = createStreamStores(connection);

    connection.emit(JSON.stringify({ streams: [rows(0, 2), rows(5, 1, "G")] }));
    connection.emit(JSON.stringify({ streams: [rows(2, 1)] }));

    const history = get(streamHistory);
    expect(history.EEG.values).toEqual([[0, 1, 2]]);
    expect(history.G.values).toEqual([[5]]);
    expect(history.G.sampleCount).toBe(1);
  });

  it("does not trim at exactly MAX_POINTS rows", () => {
    const connection = createFakeConnection();
    const { streamHistory } = createStreamStores(connection);

    connection.emit(JSON.stringify({ streams: [rows(0, MAX_POINTS)] }));

    const history = get(streamHistory).EEG;
    expect(MAX_POINTS).toBe(1250);
    expect(history.timestamps).toHaveLength(MAX_POINTS);
    expect(history.timestamps[0]).toBe(0);
  });

  it("retains exactly the newest rows on overflow and oversized batches", () => {
    const connection = createFakeConnection();
    const { streamHistory } = createStreamStores(connection);

    connection.emit(JSON.stringify({ streams: [rows(0, 1000)] }));
    connection.emit(JSON.stringify({ streams: [rows(1000, 300)] }));
    let history = get(streamHistory).EEG;
    expect(history.timestamps).toHaveLength(MAX_POINTS);
    expect(history.timestamps[0]).toBe(50);
    expect(history.values[0][0]).toBe(50);
    expect(history.values[0].at(-1)).toBe(1299);

    connection.emit(JSON.stringify({ streams: [rows(1300, 2000)] }));
    history = get(streamHistory).EEG;
    expect(history.timestamps).toHaveLength(MAX_POINTS);
    expect(history.timestamps[0]).toBe(2050);
    expect(history.values[0]).toEqual(history.timestamps);
    expect(history.sampleCount).toBe(3300);
  });

  it("trims each array at most once per batch", () => {
    const connection = createFakeConnection();
    const { streamHistory } = createStreamStores(connection);
    connection.emit(JSON.stringify({ streams: [rows(0, MAX_POINTS)] }));
    const splice = vi.spyOn(Array.prototype, "splice");

    connection.emit(JSON.stringify({ streams: [rows(MAX_POINTS, 100)] }));
    const calls = splice.mock.calls.length;
    splice.mockRestore();

    // timestamps, one column, and markers.
    expect(calls).toBe(3);
    expect(get(streamHistory).EEG.timestamps[0]).toBe(100);
  });

  it("stores non-finite and string values as NaN without mutating inputs", () => {
    const connection = createFakeConnection();
    const { streamSamples, streamHistory } = createStreamStores(connection);

    connection.emit(
      '{"streams":[{"stream_name":"EEG","samples":[[1e999,"go"],[-1e999,2]],' +
        '"timestamps":[1,2],"channel_labels":["a","b"]}]}',
    );

    const history = get(streamHistory).EEG;
    expect(history.values).toEqual([
      [NaN, NaN],
      [NaN, 2],
    ]);
    expect(history.latest).toEqual([-Infinity, 2]);
    expect(get(streamSamples).EEG.samples).toEqual([
      [Infinity, "go"],
      [-Infinity, 2],
    ]);
  });

  it("records string markers and mixed rows", () => {
    const connection = createFakeConnection();
    const { streamHistory } = createStreamStores(connection);

    connection.emit(
      JSON.stringify({
        streams: [
          {
            stream_name: "M",
            samples: [
              ["start", 1],
              [2, 3],
              ["x", "y"],
            ],
            timestamps: [1, 2, 3],
            channel_labels: ["m", "v"],
          },
        ],
      }),
    );

    const history = get(streamHistory).M;
    expect(history.values).toEqual([
      [NaN, 2, NaN],
      [1, 3, NaN],
    ]);
    expect(history.markers).toEqual([
      { timestamp: 1, channel: 0, text: "start", sampleIndex: 0 },
      { timestamp: 3, channel: 0, text: "x", sampleIndex: 2 },
      { timestamp: 3, channel: 1, text: "y", sampleIndex: 2 },
    ]);
    expect(history.latest).toEqual(["x", "y"]);
  });

  it("evicts markers by row membership with duplicate timestamps", () => {
    const connection = createFakeConnection();
    const { streamHistory } = createStreamStores(connection);
    const batch = {
      stream_name: "M",
      samples: [
        ["old"],
        ["kept"],
        ...Array.from({ length: MAX_POINTS - 1 }, () => [0]),
      ],
      timestamps: Array.from({ length: MAX_POINTS + 1 }, () => 5),
      channel_labels: ["m"],
    };

    connection.emit(JSON.stringify({ streams: [batch] }));

    const history = get(streamHistory).M;
    expect(history.timestamps).toHaveLength(MAX_POINTS);
    expect(history.markers.map((marker) => marker.text)).toEqual(["kept"]);
    expect(history.values[0][0]).toBeNaN();
  });

  it("evicts all markers once their rows leave the window", () => {
    const connection = createFakeConnection();
    const { streamHistory } = createStreamStores(connection);
    connection.emit(
      JSON.stringify({
        streams: [
          {
            stream_name: "EEG",
            samples: [["m"]],
            timestamps: [9],
            channel_labels: ["a"],
          },
        ],
      }),
    );
    connection.emit(JSON.stringify({ streams: [rows(0, MAX_POINTS)] }));

    expect(get(streamHistory).EEG.markers).toEqual([]);
  });

  it("appends timestamps for zero-channel rows", () => {
    const connection = createFakeConnection();
    const { streamHistory } = createStreamStores(connection);

    connection.emit(
      JSON.stringify({
        streams: [
          {
            stream_name: "Z",
            samples: [[], []],
            timestamps: [1, 2],
            channel_labels: [],
          },
        ],
      }),
    );

    const history = get(streamHistory).Z;
    expect(history.timestamps).toEqual([1, 2]);
    expect(history.values).toEqual([]);
    expect(history.latest).toEqual([]);
    expect(history.sampleCount).toBe(2);
  });

  it("resets retained rows when the channel layout changes", () => {
    const connection = createFakeConnection();
    const { streamHistory } = createStreamStores(connection);

    connection.emit(JSON.stringify({ streams: [rows(0, 3)] }));
    connection.emit(
      JSON.stringify({
        streams: [{ ...rows(3, 1), channel_labels: ["renamed"] }],
      }),
    );
    let history = get(streamHistory).EEG;
    expect(history.channel_labels).toEqual(["renamed"]);
    expect(history.timestamps).toEqual([3]);
    expect(history.sampleCount).toBe(4);

    connection.emit(
      JSON.stringify({
        streams: [
          {
            stream_name: "EEG",
            samples: [],
            timestamps: [],
            channel_labels: ["a", "b"],
          },
        ],
      }),
    );
    history = get(streamHistory).EEG;
    expect(history.values).toEqual([[], []]);
    expect(history.latest).toEqual([]);
    expect(history.sampleCount).toBe(4);
  });

  it("keeps latest and history for an empty batch", () => {
    const connection = createFakeConnection();
    const { streamHistory, streamSamples } = createStreamStores(connection);

    connection.emit(JSON.stringify({ streams: [rows(0, 2)] }));
    connection.emit(JSON.stringify({ streams: [rows(2, 0)] }));

    const history = get(streamHistory).EEG;
    expect(history.latest).toEqual([1]);
    expect(history.timestamps).toEqual([0, 1]);
    expect(history.sampleCount).toBe(2);
    expect(get(streamSamples).EEG.samples).toEqual([]);
  });

  it("notifies subscribers with new references", () => {
    const connection = createFakeConnection();
    const { streamHistory } = createStreamStores(connection);
    const seen: unknown[] = [];
    const unsubscribe = streamHistory.subscribe((value) => {
      seen.push(value.EEG);
    });

    connection.emit(JSON.stringify({ streams: [rows(0, 1)] }));
    connection.emit(JSON.stringify({ streams: [rows(1, 1)] }));
    unsubscribe();

    expect(seen).toHaveLength(3);
    expect(seen[1]).not.toBe(seen[2]);
  });

  it("is not populated by discovery", () => {
    const connection = createFakeConnection();
    const { streamHistory } = createStreamStores(connection);

    connection.emit(
      JSON.stringify({ type: "discover_result", streams: ["EEG"] }),
    );

    expect(get(streamHistory)).toEqual({});
  });

  it("stops updating history and latest batches after stop", () => {
    const connection = createFakeConnection();
    const { streamHistory, streamSamples, stop } =
      createStreamStores(connection);

    connection.emit(JSON.stringify({ streams: [rows(0, 1)] }));
    stop();
    connection.emit(JSON.stringify({ streams: [rows(1, 1)] }));

    expect(get(streamHistory).EEG.timestamps).toEqual([0]);
    expect(get(streamSamples).EEG.samples).toEqual([[0]]);
  });
});
