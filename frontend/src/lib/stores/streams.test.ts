/** Unit tests for the live stream-data stores. */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { get } from "svelte/store";
import { writable } from "svelte/store";

import { parseServerMessage, type StreamData } from "$lib/protocol";
import { classifyStream } from "$lib/stream-classification";
import {
  createWebSocketStore,
  type ConnectionStatus,
  type MessageHandler,
  type WebSocketStore,
} from "$lib/stores/websocket";
import {
  MAX_MARKERS,
  MAX_POINTS,
  createStreamStores,
} from "$lib/stores/streams";

/**
 * Minimal connection-store double that lets a test emit server messages.
 *
 * @returns A WebSocket store double with an `emit` helper for test messages.
 */
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

/**
 * Builds a one-channel batch whose values and timestamps equal row numbers.
 *
 * @param start - First row value and timestamp.
 * @param count - Number of rows to generate.
 * @param name - Stream name, defaulting to `EEG`.
 * @returns A one-channel batch with consecutive values and timestamps.
 */
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
      category: "numeric",
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

    // timestamps and one column.
    expect(calls).toBe(2);
    expect(get(streamHistory).EEG.timestamps[0]).toBe(100);
  });

  it("stores non-finite numbers as NaN without mutating inputs", () => {
    const connection = createFakeConnection();
    const { streamSamples, streamHistory } = createStreamStores(connection);

    connection.emit(
      '{"streams":[{"stream_name":"EEG","samples":[[1e999,1],[-1e999,2]],' +
        '"timestamps":[1,2],"channel_labels":["a","b"]}]}',
    );

    const history = get(streamHistory).EEG;
    expect(history.values).toEqual([
      [NaN, NaN],
      [1, 2],
    ]);
    expect(history.markers).toEqual([]);
    expect(history.latest).toEqual([-Infinity, 2]);
    expect(get(streamSamples).EEG.samples).toEqual([
      [Infinity, 1],
      [-Infinity, 2],
    ]);
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

/**
 * Builds a marker batch with one channel per entry in the first row.
 *
 * @param values - Sample rows containing marker values.
 * @param start - First row timestamp, defaulting to zero.
 * @param name - Stream name, defaulting to `M`.
 * @param streamType - Declared stream type, defaulting to `Markers`.
 * @returns A marker batch with timestamps based on row indices.
 */
function markerBatch(
  values: (number | string)[][],
  start = 0,
  name = "M",
  streamType: string | undefined = "Markers",
) {
  return {
    stream_name: name,
    samples: values,
    timestamps: values.map((_, i) => start + i),
    channel_labels: (values[0] ?? ["m"]).map((_, i) => `m${i}`),
    ...(streamType === undefined ? {} : { stream_type: streamType }),
  };
}

/**
 * Builds a one-channel marker batch of `count` string events.
 *
 * @param start - First event number and timestamp.
 * @param count - Number of events to generate.
 * @param name - Stream name, defaulting to `M`.
 * @returns A marker batch containing consecutive string events.
 */
function markerRows(start: number, count: number, name = "M") {
  return markerBatch(
    Array.from({ length: count }, (_, i) => [`e${start + i}`]),
    start,
    name,
  );
}

describe("streamHistory markers", () => {
  it("stores one event per channel, row then channel order", () => {
    const connection = createFakeConnection();
    const { streamHistory } = createStreamStores(connection);

    connection.emit(
      JSON.stringify({
        streams: [
          markerBatch(
            [
              ["start", 1],
              [2, "y"],
            ],
            5,
            "M",
          ),
        ],
      }),
    );

    const history = get(streamHistory).M;
    expect(history).toEqual({
      category: "marker",
      channel_labels: ["m0", "m1"],
      timestamps: [],
      values: [],
      latest: [2, "y"],
      markers: [
        { timestamp: 5, value: "start", channelIndex: 0 },
        { timestamp: 5, value: 1, channelIndex: 1 },
        { timestamp: 6, value: 2, channelIndex: 0 },
        { timestamp: 6, value: "y", channelIndex: 1 },
      ],
      sampleCount: 2,
    });
  });

  it("keeps numeric values on a Markers-typed stream as numbers", () => {
    const connection = createFakeConnection();
    const { streamHistory } = createStreamStores(connection);

    connection.emit(JSON.stringify({ streams: [markerBatch([[7], [8]])] }));

    expect(get(streamHistory).M.markers).toEqual([
      { timestamp: 0, value: 7, channelIndex: 0 },
      { timestamp: 1, value: 8, channelIndex: 0 },
    ]);
  });

  it("caps events, not rows, at MAX_MARKERS", () => {
    const connection = createFakeConnection();
    const { streamHistory } = createStreamStores(connection);
    const half = MAX_MARKERS / 2;
    const twoChannel = Array.from({ length: half }, (_, i) => [i, `s${i}`]);

    connection.emit(JSON.stringify({ streams: [markerBatch(twoChannel)] }));
    let history = get(streamHistory).M;
    expect(MAX_MARKERS).toBe(250);
    expect(history.markers).toHaveLength(MAX_MARKERS);
    expect(history.markers[0]).toEqual({
      timestamp: 0,
      value: 0,
      channelIndex: 0,
    });

    connection.emit(
      JSON.stringify({ streams: [markerBatch([["a", "b"]], half)] }),
    );
    history = get(streamHistory).M;
    expect(history.markers).toHaveLength(MAX_MARKERS);
    expect(history.markers[0]).toEqual({
      timestamp: 1,
      value: 1,
      channelIndex: 0,
    });
    expect(history.markers.at(-1)).toEqual({
      timestamp: half,
      value: "b",
      channelIndex: 1,
    });
    expect(history.sampleCount).toBe(half + 1);
  });

  it("keeps only the newest events from an oversized batch, trimming once", () => {
    const connection = createFakeConnection();
    const { streamHistory } = createStreamStores(connection);
    connection.emit(JSON.stringify({ streams: [markerRows(0, 10)] }));
    const splice = vi.spyOn(Array.prototype, "splice");

    connection.emit(JSON.stringify({ streams: [markerRows(10, 400)] }));
    const calls = splice.mock.calls.length;
    splice.mockRestore();

    const history = get(streamHistory).M;
    expect(calls).toBe(1);
    expect(history.markers).toHaveLength(MAX_MARKERS);
    expect(history.markers[0]).toEqual({
      timestamp: 160,
      value: "e160",
      channelIndex: 0,
    });
    expect(history.markers.at(-1)).toEqual({
      timestamp: 409,
      value: "e409",
      channelIndex: 0,
    });
    expect(history.sampleCount).toBe(410);
  });

  it("does not mutate the incoming batch", () => {
    const connection = createFakeConnection();
    const { streamSamples, streamHistory } = createStreamStores(connection);
    const batch = markerBatch([["a", 1]]);

    connection.emit(JSON.stringify({ streams: [batch] }));
    get(streamHistory).M.latest.push("extra");

    expect(get(streamSamples).M).toEqual(batch);
  });

  it("keeps marker and numeric streams independent, with repeated names", () => {
    const connection = createFakeConnection();
    const { streamHistory } = createStreamStores(connection);

    connection.emit(
      JSON.stringify({
        streams: [markerRows(0, 1), rows(0, 1), markerRows(1, 2)],
      }),
    );

    const history = get(streamHistory);
    expect(history.M.markers.map((marker) => marker.value)).toEqual([
      "e0",
      "e1",
      "e2",
    ]);
    expect(history.M.sampleCount).toBe(3);
    expect(history.EEG.values).toEqual([[0]]);
    expect(history.EEG.markers).toEqual([]);
  });

  it("handles marker streams named like prototype properties", () => {
    const connection = createFakeConnection();
    const { streamHistory, orderedStreams } = createStreamStores(connection);

    connection.emit(
      JSON.stringify({
        streams: [markerRows(0, 1, "__proto__"), markerRows(0, 1, "toString")],
      }),
    );
    connection.emit(
      JSON.stringify({ streams: [markerRows(1, 1, "__proto__")] }),
    );

    const history = get(streamHistory);
    expect(Object.keys(history)).toEqual(["__proto__", "toString"]);
    const proto = Object.getOwnPropertyDescriptor(history, "__proto__")?.value;
    expect(proto.markers).toHaveLength(2);
    expect(history["toString"].markers).toHaveLength(1);
    expect(get(orderedStreams).map((stream) => stream.stream_name)).toEqual([
      "__proto__",
      "toString",
    ]);
  });

  it("keeps the newest 250 of 252 events, starting mid-row", () => {
    const connection = createFakeConnection();
    const { streamHistory } = createStreamStores(connection);
    const batch = threeChannelMarkers(0, 84);

    connection.emit(JSON.stringify({ streams: [batch] }));

    const history = get(streamHistory).M;
    expect(history.markers).toHaveLength(MAX_MARKERS);
    const first = history.markers[0];
    expect(first).toEqual({ timestamp: 0, value: "r0c2", channelIndex: 2 });
    expect(history.channel_labels[first.channelIndex]).toBe("m2");
    expect(history.markers[1]).toEqual({
      timestamp: 1,
      value: "r1c0",
      channelIndex: 0,
    });
    expect(history.markers.at(-1)).toEqual({
      timestamp: 83,
      value: "r83c2",
      channelIndex: 2,
    });
    expect(history.sampleCount).toBe(84);
    expect(history.latest).toEqual(["r83c0", "r83c1", "r83c2"]);
  });

  it("caps events across batches with correct channel indices", () => {
    const connection = createFakeConnection();
    const { streamHistory } = createStreamStores(connection);

    connection.emit(JSON.stringify({ streams: [threeChannelMarkers(0, 80)] }));
    connection.emit(JSON.stringify({ streams: [threeChannelMarkers(80, 4)] }));

    const history = get(streamHistory).M;
    expect(history.markers).toHaveLength(MAX_MARKERS);
    expect(history.markers[0]).toEqual({
      timestamp: 0,
      value: "r0c2",
      channelIndex: 2,
    });
    expect(history.markers.at(-1)).toEqual({
      timestamp: 83,
      value: "r83c2",
      channelIndex: 2,
    });
    expect(history.sampleCount).toBe(84);
  });

  it("discards old markers when the label layout changes", () => {
    const connection = createFakeConnection();
    const { streamHistory } = createStreamStores(connection);
    connection.emit(JSON.stringify({ streams: [threeChannelMarkers(0, 2)] }));

    connection.emit(JSON.stringify({ streams: [markerBatch([["solo"]], 2)] }));

    const history = get(streamHistory).M;
    expect(history.channel_labels).toEqual(["m0"]);
    expect(history.markers).toEqual([
      { timestamp: 2, value: "solo", channelIndex: 0 },
    ]);
    expect(history.sampleCount).toBe(3);
  });
});

/**
 * Builds a three-channel marker batch whose values name their row and channel.
 *
 * @param start - First row number and timestamp.
 * @param count - Number of rows to generate.
 * @returns A marker batch with values like `r0c2` and labels `m0`–`m2`.
 */
function threeChannelMarkers(start: number, count: number) {
  return markerBatch(
    Array.from({ length: count }, (_, i) =>
      [0, 1, 2].map((channel) => `r${start + i}c${channel}`),
    ),
    start,
  );
}

describe("streamHistory category transitions", () => {
  it("drops numeric rows and stores the whole switching batch as events", () => {
    const connection = createFakeConnection();
    const { streamHistory } = createStreamStores(connection);

    connection.emit(JSON.stringify({ streams: [rows(0, 3)] }));
    connection.emit(
      JSON.stringify({
        streams: [
          {
            ...rows(3, 2),
            samples: [[3], ["go"]],
          },
        ],
      }),
    );

    let history = get(streamHistory).EEG;
    expect(history.category).toBe("marker");
    expect(history.timestamps).toEqual([]);
    expect(history.values).toEqual([]);
    expect(history.markers).toEqual([
      { timestamp: 3, value: 3, channelIndex: 0 },
      { timestamp: 4, value: "go", channelIndex: 0 },
    ]);
    expect(history.latest).toEqual(["go"]);
    expect(history.sampleCount).toBe(5);

    // Sticky: an all-numeric batch with the same layout stays a marker.
    connection.emit(JSON.stringify({ streams: [rows(5, 1)] }));
    history = get(streamHistory).EEG;
    expect(history.category).toBe("marker");
    expect(history.markers).toHaveLength(3);

    // A type change resets to numeric, keeping the cumulative count.
    connection.emit(
      JSON.stringify({ streams: [{ ...rows(6, 2), stream_type: "EEG" }] }),
    );
    history = get(streamHistory).EEG;
    expect(history.category).toBe("eeg");
    expect(history.markers).toEqual([]);
    expect(history.timestamps).toEqual([6, 7]);
    expect(history.values).toEqual([[6, 7]]);
    expect(history.latest).toEqual([7]);
    expect(history.sampleCount).toBe(8);
  });

  it("resets latest on a type change with an empty batch", () => {
    const connection = createFakeConnection();
    const { streamHistory } = createStreamStores(connection);

    connection.emit(JSON.stringify({ streams: [rows(0, 2)] }));
    connection.emit(
      JSON.stringify({ streams: [{ ...rows(2, 0), stream_type: "Markers" }] }),
    );

    const history = get(streamHistory).EEG;
    expect(history.category).toBe("marker");
    expect(history.latest).toEqual([]);
    expect(history.timestamps).toEqual([]);
    expect(history.sampleCount).toBe(2);
  });
});

describe("clearHistory", () => {
  it("empties buffers but keeps latest, counts, category, and other stores", () => {
    const connection = createFakeConnection();
    const stores = createStreamStores(connection);
    const disconnect = vi.spyOn(connection, "disconnect");
    connection.emit(
      JSON.stringify({ type: "discover_result", streams: ["EEG", "M"] }),
    );
    connection.emit(
      JSON.stringify({ streams: [rows(0, 2), markerBatch([["x", 1]])] }),
    );
    const samples = get(stores.streamSamples);
    const ordered = get(stores.orderedStreams);
    const seen: unknown[] = [];
    const unsubscribe = stores.streamHistory.subscribe((value) => {
      seen.push(value);
    });

    stores.clearHistory();
    unsubscribe();

    expect(seen).toHaveLength(2);
    const history = get(stores.streamHistory);
    expect(history.EEG).toEqual({
      category: "numeric",
      channel_labels: ["a"],
      timestamps: [],
      values: [[]],
      latest: [1],
      markers: [],
      sampleCount: 2,
    });
    expect(history.M).toEqual({
      category: "marker",
      channel_labels: ["m0", "m1"],
      timestamps: [],
      values: [],
      latest: ["x", 1],
      markers: [],
      sampleCount: 1,
    });
    expect(get(stores.streamSamples)).toBe(samples);
    expect(get(stores.orderedStreams)).toBe(ordered);
    expect(get(stores.discoveredStreams)).toEqual(["EEG", "M"]);
    expect(disconnect).not.toHaveBeenCalled();

    connection.emit(JSON.stringify({ streams: [rows(2, 1)] }));
    const after = get(stores.streamHistory).EEG;
    expect(after.timestamps).toEqual([2]);
    expect(after.values).toEqual([[2]]);
    expect(after.sampleCount).toBe(3);
  });

  it("keeps a string-triggered EEG-typed marker sticky after clearing", () => {
    const connection = createFakeConnection();
    const stores = createStreamStores(connection);
    const labels = ["trig", "code"];
    const stringBatch: StreamData = {
      stream_name: "Trig",
      stream_type: "EEG",
      samples: [["go", 1]],
      timestamps: [0],
      channel_labels: labels,
    };
    const numericBatch: StreamData = {
      ...stringBatch,
      samples: [
        [7, 8],
        [9, 10],
      ],
      timestamps: [1, 2],
    };
    // Negative control: without retained state this batch is plain EEG.
    expect(classifyStream(undefined, numericBatch).category).toBe("eeg");

    connection.emit(JSON.stringify({ streams: [stringBatch] }));
    expect(get(stores.streamHistory).Trig.category).toBe("marker");
    stores.clearHistory();
    connection.emit(JSON.stringify({ streams: [numericBatch] }));

    expect(get(stores.streamHistory).Trig).toEqual({
      category: "marker",
      channel_labels: labels,
      timestamps: [],
      values: [],
      latest: [9, 10],
      markers: [
        { timestamp: 1, value: 7, channelIndex: 0 },
        { timestamp: 1, value: 8, channelIndex: 1 },
        { timestamp: 2, value: 9, channelIndex: 0 },
        { timestamp: 2, value: 10, channelIndex: 1 },
      ],
      sampleCount: 3,
    });
    expect(get(stores.orderedStreams)).toEqual([numericBatch]);
  });

  it("keeps prototype-named streams as own keys", () => {
    const connection = createFakeConnection();
    const { streamHistory, clearHistory } = createStreamStores(connection);
    connection.emit(JSON.stringify({ streams: [rows(0, 1, "__proto__")] }));

    clearHistory();

    const history = get(streamHistory);
    expect(Object.keys(history)).toEqual(["__proto__"]);
    const proto = Object.getOwnPropertyDescriptor(history, "__proto__")?.value;
    expect(proto).toMatchObject({ timestamps: [], values: [[]] });
  });
});

describe("orderedStreams", () => {
  it("orders EEG, other numeric, then markers, by name within each", () => {
    const connection = createFakeConnection();
    const { orderedStreams } = createStreamStores(connection);

    connection.emit(
      JSON.stringify({
        streams: [
          markerRows(0, 1, "B-mark"),
          rows(0, 1, "Z-num"),
          { ...rows(0, 1, "Y-eeg"), stream_type: "eeg" },
          rows(0, 1, "A-num"),
          markerRows(0, 1, "A-mark"),
          { ...rows(0, 1, "X-eeg"), stream_type: "EEG" },
        ],
      }),
    );

    expect(get(orderedStreams).map((stream) => stream.stream_name)).toEqual([
      "X-eeg",
      "Y-eeg",
      "A-num",
      "Z-num",
      "A-mark",
      "B-mark",
    ]);
  });

  it("lists latest batches and reorders when a stream becomes a marker", () => {
    const connection = createFakeConnection();
    const { orderedStreams } = createStreamStores(connection);
    connection.emit(JSON.stringify({ streams: [rows(0, 1, "A"), rows(0, 1)] }));

    const next = { ...rows(1, 1, "A"), samples: [["go"]] };
    connection.emit(JSON.stringify({ streams: [next] }));

    expect(get(orderedStreams)).toEqual([rows(0, 1), next]);
  });

  it("is not populated by discovery and stops with the stores", () => {
    const connection = createFakeConnection();
    const { orderedStreams, stop } = createStreamStores(connection);

    connection.emit(
      JSON.stringify({ type: "discover_result", streams: ["EEG"] }),
    );
    expect(get(orderedStreams)).toEqual([]);

    connection.emit(JSON.stringify({ streams: [rows(0, 1)] }));
    stop();
    connection.emit(JSON.stringify({ streams: [rows(1, 1, "B")] }));
    expect(get(orderedStreams)).toEqual([rows(0, 1)]);
  });
});

/** Minimal controllable WebSocket double, mirroring `websocket.test.ts`. */
class MockWebSocket {
  static readonly OPEN = 1;
  static instances: MockWebSocket[] = [];

  readyState = 0;
  onopen: (() => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;

  constructor(public url: string) {
    MockWebSocket.instances.push(this);
  }

  send(): void {}

  close(): void {
    this.readyState = 3;
  }

  open(): void {
    this.readyState = MockWebSocket.OPEN;
    this.onopen?.();
  }

  emitClose(): void {
    this.onclose?.();
  }

  emitMessage(data: string): void {
    this.onmessage?.({ data } as MessageEvent);
  }
}

/**
 * Serializes a data frame containing the given stream batches.
 *
 * @param streams - Batches to include in the frame.
 * @returns The JSON frame text.
 */
function frame(...streams: StreamData[]): string {
  return JSON.stringify({ streams });
}

/**
 * Lists the stream names present in every seen-stream store.
 *
 * @param stores - Stores to inspect.
 * @returns Sorted names from samples, history, and display order.
 */
function seenNames(stores: ReturnType<typeof createStreamStores>) {
  return {
    samples: Object.keys(get(stores.streamSamples)).sort(),
    history: Object.keys(get(stores.streamHistory)).sort(),
    ordered: get(stores.orderedStreams).map((stream) => stream.stream_name),
  };
}

describe("seen streams", () => {
  const ALL_SEEN = {
    samples: ["EEG", "M"],
    history: ["EEG", "M"],
    ordered: ["EEG", "M"],
  };

  beforeEach(() => {
    MockWebSocket.instances = [];
    vi.stubGlobal("WebSocket", MockWebSocket);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("keeps a quiet marker stream through sparse and empty frames", () => {
    const connection = createFakeConnection();
    const stores = createStreamStores(connection);
    const marker = markerBatch([["go"]]);
    connection.emit(frame(rows(0, 1), marker));

    connection.emit(frame(rows(1, 2)));
    connection.emit(JSON.stringify({ streams: [] }));

    expect(seenNames(stores)).toEqual(ALL_SEEN);
    expect(get(stores.streamSamples).M).toEqual(marker);
    const history = get(stores.streamHistory);
    expect(history.M.category).toBe("marker");
    expect(history.M.markers).toEqual([
      { timestamp: 0, value: "go", channelIndex: 0 },
    ]);
    expect(history.EEG.timestamps).toEqual([0, 1, 2]);
  });

  it("keeps membership and history across a real socket reconnect", () => {
    const connection = createWebSocketStore("ws://localhost:8765");
    const stores = createStreamStores(connection);
    connection.connect();
    const first = MockWebSocket.instances[0];
    first.open();
    first.emitMessage(frame(rows(0, 1), markerBatch([["go"]])));

    first.emitClose();
    expect(get(connection)).toBe("closed");
    expect(seenNames(stores)).toEqual(ALL_SEEN);

    connection.connect();
    const second = MockWebSocket.instances[1];
    expect(second.url).toBe("ws://localhost:8765");
    second.open();
    second.emitMessage(frame(rows(1, 1)));

    expect(get(connection)).toBe("open");
    expect(seenNames(stores)).toEqual(ALL_SEEN);
    const history = get(stores.streamHistory);
    expect(history.EEG.timestamps).toEqual([0, 1]);
    expect(history.EEG.sampleCount).toBe(2);
    expect(history.M.category).toBe("marker");
    expect(history.M.markers).toHaveLength(1);
    stores.stop();
  });

  it("keeps membership after clearHistory", () => {
    const connection = createFakeConnection();
    const stores = createStreamStores(connection);
    connection.emit(frame(rows(0, 1), markerBatch([["go"]])));

    stores.clearHistory();

    expect(seenNames(stores)).toEqual(ALL_SEEN);
  });
});
