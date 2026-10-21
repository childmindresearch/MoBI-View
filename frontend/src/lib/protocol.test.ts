/** Unit tests for the WebSocket protocol module. */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  DEFAULT_WS_URL,
  discoverCommand,
  isDataFrame,
  isDiscoverResult,
  parseServerMessage,
  type ServerMessage,
  type StreamData,
} from "$lib/protocol";

const numericStream: StreamData = {
  stream_name: "EEG",
  samples: [
    [1, 2],
    [3, 4],
  ],
  timestamps: [10, 10.004],
  channel_labels: ["a", "b"],
  stream_type: "EEG",
  channel_units: ["uV", "uV"],
};

const markerStream: StreamData = {
  stream_name: "Markers",
  samples: [["start"], ["stop"]],
  timestamps: [10, 11],
  channel_labels: ["event"],
};

const invalidStreamEntries = [
  null,
  42,
  {},
  { ...numericStream, stream_name: undefined },
  { ...numericStream, stream_name: 42 },
  { ...numericStream, samples: undefined },
  { ...numericStream, samples: {} },
  { ...numericStream, samples: [1, 2] },
  { ...numericStream, samples: [[null, 2]] },
  { ...numericStream, samples: [[true, 2]] },
  { ...numericStream, samples: [[1], [3, 4]] },
  {
    ...numericStream,
    samples: [
      [1, 2],
      [3, 4, 5],
    ],
  },
  { ...numericStream, timestamps: undefined },
  { ...numericStream, timestamps: ["invalid"] },
  { ...numericStream, timestamps: [10] },
  { ...numericStream, timestamps: [10, 11, 12] },
  { ...numericStream, channel_labels: [42] },
  { ...numericStream, stream_type: 42 },
  { ...numericStream, channel_units: [42] },
  { ...numericStream, channel_units: ["uV"] },
  { ...numericStream, channel_units: ["uV", "uV", "uV"] },
];

beforeEach(() => {
  vi.spyOn(console, "warn").mockImplementation(() => {});
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("discoverCommand", () => {
  it("builds the discover command payload", () => {
    expect(discoverCommand()).toEqual({ command: "discover" });
  });
});

describe("DEFAULT_WS_URL", () => {
  it("points at the backend default endpoint", () => {
    expect(DEFAULT_WS_URL).toBe("ws://localhost:8765");
  });
});

describe("parseServerMessage", () => {
  it("parses a discover_result message", () => {
    const raw = JSON.stringify({
      type: "discover_result",
      streams: ["EEG", "Markers"],
    });

    expect(parseServerMessage(raw)).toEqual({
      type: "discover_result",
      streams: ["EEG", "Markers"],
    });
  });

  it("parses a batched numeric frame with metadata", () => {
    const frame = { streams: [numericStream] };

    expect(parseServerMessage(JSON.stringify(frame))).toEqual(frame);
    expect(console.warn).not.toHaveBeenCalled();
  });

  it("parses a marker batch without optional metadata or string coercion", () => {
    const frame = { streams: [markerStream] };

    expect(parseServerMessage(JSON.stringify(frame))).toEqual(frame);
    expect(console.warn).not.toHaveBeenCalled();
  });

  it("parses an empty data frame", () => {
    expect(parseServerMessage(JSON.stringify({ streams: [] }))).toEqual({
      streams: [],
    });
  });

  it.each(invalidStreamEntries)(
    "drops an invalid entry without discarding valid streams (%j)",
    (entry) => {
      const raw = JSON.stringify({
        streams: [numericStream, entry, markerStream],
      });

      expect(parseServerMessage(raw)).toEqual({
        streams: [numericStream, markerStream],
      });
      expect(console.warn).toHaveBeenCalledExactlyOnceWith(
        "Dropped invalid stream entries from WebSocket data frame",
        1,
      );
    },
  );

  it("returns an empty data frame when every stream entry is invalid", () => {
    const raw = JSON.stringify({ streams: [null, {}] });

    expect(parseServerMessage(raw)).toEqual({ streams: [] });
    expect(console.warn).toHaveBeenCalledExactlyOnceWith(
      "Dropped invalid stream entries from WebSocket data frame",
      2,
    );
  });

  it("returns null for invalid JSON", () => {
    expect(parseServerMessage("not json")).toBeNull();
    expect(console.warn).toHaveBeenCalledExactlyOnceWith(
      "Received invalid WebSocket JSON",
    );
  });

  it.each([
    null,
    42,
    true,
    { foo: "bar" },
    { streams: null },
    { type: "discover_result", streams: ["EEG", 42] },
  ])("returns null for an invalid message (%j)", (message) => {
    expect(parseServerMessage(JSON.stringify(message))).toBeNull();
    expect(console.warn).toHaveBeenCalledExactlyOnceWith(
      "Received an invalid WebSocket server message",
    );
  });

  it.each(["1e400", "-1e400"])(
    "drops a stream with timestamp %s while retaining valid sibilings",
    (timestamp) => {
      const invalid = `{
        "stream_name": "Invalid",
        "samples": [[1]],
        "timestamps": [${timestamp}],
        "channel_labels": ["a"]
      }`;
      const raw = `{
        "streams": [${invalid}, ${JSON.stringify(numericStream)}]
      }`;

      expect(parseServerMessage(raw)).toEqual({
        streams: [numericStream],
      });
      expect(console.warn).toHaveBeenCalledExactlyOnceWith(
        "Dropped invalid stream entries from WebSocket data frame",
        1,
      );
    },
  );

  it.each(["NaN", "Infinity", "-Infinity"])(
    "rejects the entire payload containing the invalid JSON token %s",
    (token) => {
      const invalid = `{
        "stream_name": "Invalid",
        "samples": [[${token}]],
        "timestamps": [10],
        "channel_labels": ["a"]
      }`;
      const raw = `{
        "streams": [${invalid}, ${JSON.stringify(numericStream)}]
      }`;

      expect(parseServerMessage(raw)).toBeNull();
      expect(console.warn).toHaveBeenCalledExactlyOnceWith(
        "Received invalid WebSocket JSON",
      );
    },
  );
});

describe("isDiscoverResult", () => {
  it("returns true for a discover_result message", () => {
    const message: ServerMessage = { type: "discover_result", streams: [] };

    expect(isDiscoverResult(message)).toBe(true);
  });

  it("returns false for a data frame message", () => {
    const message: ServerMessage = { streams: [] };

    expect(isDiscoverResult(message)).toBe(false);
  });
});

describe("isDataFrame", () => {
  it("returns true for a data frame message", () => {
    const message: ServerMessage = { streams: [] };

    expect(isDataFrame(message)).toBe(true);
  });

  it("returns false for a discover_result message", () => {
    const message: ServerMessage = { type: "discover_result", streams: [] };

    expect(isDataFrame(message)).toBe(false);
  });

  it("returns true for a frame containing numeric and marker batches", () => {
    expect(isDataFrame({ streams: [numericStream, markerStream] })).toBe(true);
  });
});
