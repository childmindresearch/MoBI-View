/** Unit tests for the WebSocket protocol module. */

import { describe, expect, it } from "vitest";

import {
  DEFAULT_WS_URL,
  discoverCommand,
  isDataFrame,
  isDiscoverResult,
  parseServerMessage,
  type ServerMessage,
} from "$lib/protocol";

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

  it("parses a data frame message", () => {
    const raw = JSON.stringify({
      streams: [
        { stream_name: "EEG", data: [1, 2], channel_labels: ["a", "b"] },
      ],
    });

    expect(parseServerMessage(raw)).toEqual({
      streams: [
        { stream_name: "EEG", data: [1, 2], channel_labels: ["a", "b"] },
      ],
    });
  });

  it("returns null for invalid JSON", () => {
    expect(parseServerMessage("not json")).toBeNull();
  });

  it("returns null for a JSON value that is not an object", () => {
    expect(parseServerMessage("42")).toBeNull();
  });

  it("returns null for an unrecognised message shape", () => {
    expect(parseServerMessage(JSON.stringify({ foo: "bar" }))).toBeNull();
  });
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
});
