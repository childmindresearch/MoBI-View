/** Tests stream classification and display ordering helpers. */

import { describe, expect, it } from "vitest";

import type { SampleValue, StreamData } from "$lib/protocol";
import {
  classifyStream,
  compareStreams,
  isEegType,
  isMarkersType,
  orderStreamNames,
  updateClassifications,
  type StreamClassification,
} from "$lib/stream-classification";

/**
 * Builds a batch with timestamps matching each row's zero-based index.
 *
 * @param samples - Sample rows for the batch.
 * @param streamType - Optional declared stream type.
 * @param name - Stream name, defaulting to `s`.
 * @param labels - Channel labels, defaulting to `c0`.
 * @returns A stream batch with timestamps generated from zero.
 */
function batch(
  samples: SampleValue[][],
  streamType?: string,
  name = "s",
  labels = ["c0"],
): StreamData {
  return {
    stream_name: name,
    samples,
    timestamps: samples.map((_, i) => i),
    channel_labels: labels,
    ...(streamType === undefined ? {} : { stream_type: streamType }),
  };
}

describe("type checks", () => {
  it("matches EEG and Markers case-insensitively and exactly", () => {
    expect(isEegType("eeg")).toBe(true);
    expect(isEegType("EeG")).toBe(true);
    expect(isEegType("EEG2")).toBe(false);
    expect(isEegType(undefined)).toBe(false);
    expect(isMarkersType("MARKERS")).toBe(true);
    expect(isMarkersType("Marker")).toBe(false);
    expect(isMarkersType("MyMarkers")).toBe(false);
  });
});

describe("classifyStream", () => {
  it("classifies by type and content", () => {
    expect(classifyStream(undefined, batch([[1]], "eeg")).category).toBe("eeg");
    expect(classifyStream(undefined, batch([[1]], "Audio")).category).toBe(
      "numeric",
    );
    expect(classifyStream(undefined, batch([[1]])).category).toBe("numeric");
    expect(classifyStream(undefined, batch([], "markers")).category).toBe(
      "marker",
    );
    expect(classifyStream(undefined, batch([[1], ["x"]])).category).toBe(
      "marker",
    );
  });

  it("gives marker priority over EEG", () => {
    expect(classifyStream(undefined, batch([["x"]], "EEG")).category).toBe(
      "marker",
    );
  });

  it("keeps marker sticky across empty and numeric batches", () => {
    let state = classifyStream(undefined, batch([["x"]], "EEG"));
    state = classifyStream(state, batch([], "EEG"));
    expect(state.category).toBe("marker");
    state = classifyStream(state, batch([[1]], "EEG"));
    expect(state.category).toBe("marker");
  });

  it("resets on stream_type or layout change", () => {
    const marker = classifyStream(undefined, batch([["x"]], "EEG"));
    expect(classifyStream(marker, batch([[1]], "eeg")).category).toBe("eeg");
    expect(classifyStream(marker, batch([[1]])).category).toBe("numeric");
    expect(
      classifyStream(marker, batch([[1]], "EEG", "s", ["c1"])).category,
    ).toBe("eeg");
  });

  it("treats missing stream_type as distinct from empty string", () => {
    const marker = classifyStream(undefined, batch([["x"]]));
    expect(classifyStream(marker, batch([[1]])).category).toBe("marker");
    expect(classifyStream(marker, batch([[1]], "")).category).toBe("numeric");
  });

  it("copies channel labels", () => {
    const stream = batch([[1]]);
    const state: StreamClassification = classifyStream(undefined, stream);
    stream.channel_labels.push("c1");
    expect(state.channelLabels).toEqual(["c0"]);
  });
});

describe("updateClassifications", () => {
  it("handles inherited-name keys and does not mutate input", () => {
    const current = {};
    const next = updateClassifications(current, [
      batch([["x"]], undefined, "__proto__"),
      batch([[1]], undefined, "constructor"),
      batch([[1]], undefined, "constructor"),
    ]);
    expect(current).toEqual({});
    expect(Object.keys(next).sort()).toEqual(["__proto__", "constructor"]);
    expect(Object.getPrototypeOf(next)).toBe(Object.prototype);
    expect(orderStreamNames(next)).toEqual(["constructor", "__proto__"]);
  });

  it("keeps sticky markers across frames", () => {
    const first = updateClassifications({}, [batch([["x"]], "EEG", "m")]);
    const second = updateClassifications(first, [batch([], "EEG", "m")]);
    expect(second.m.category).toBe("marker");
  });
});

describe("ordering", () => {
  it("sorts EEG, numeric, markers, then name", () => {
    const state = updateClassifications({}, [
      batch([["x"]], undefined, "aMarker"),
      batch([[1]], "Audio", "b"),
      batch([[1]], "EEG", "z"),
      batch([[1]], undefined, "a"),
      batch([[1]], "eeg", "y"),
    ]);
    expect(orderStreamNames(state)).toEqual(["y", "z", "a", "b", "aMarker"]);
  });

  it("compares equal names as zero", () => {
    const entry = { name: "a", category: "eeg" as const };
    expect(compareStreams(entry, entry)).toBe(0);
  });
});
