/** Tests for the page-local live chart selection, data, and options helpers. */

import { describe, expect, it } from "vitest";

import type { StreamHistory } from "$lib/stores/streams";
import type { StreamCategory } from "$lib/stream-classification";

import {
  appendBounded,
  buildLiveChartView,
  selectChartStream,
} from "./chart-data";

/**
 * Builds a stream history with aligned numeric columns.
 *
 * @param category - Stream category.
 * @param labels - Channel labels.
 * @param rows - Number of rows to fill.
 * @returns A history object.
 */
function history(
  category: StreamCategory,
  labels: string[] = ["a", "b"],
  rows = 3,
): StreamHistory {
  const timestamps = Array.from({ length: rows }, (_, i) => i);
  return {
    category,
    channel_labels: labels,
    timestamps,
    values: labels.map((_, c) => timestamps.map((t) => t + c)),
    latest: [],
    markers: [],
    sampleCount: rows,
  };
}

describe("selectChartStream", () => {
  it("prefers EEG, then alphabetical numeric, and skips markers", () => {
    const map = new Map([
      ["zeta", history("numeric")],
      ["alpha", history("numeric")],
      ["aaa", history("marker")],
    ]);
    expect(selectChartStream(map)).toBe("alpha");
    map.set("yeeg", history("eeg"));
    expect(selectChartStream(map)).toBe("yeeg");
  });

  it("returns undefined for an empty map or markers only", () => {
    expect(selectChartStream(new Map())).toBeUndefined();
    expect(
      selectChartStream(new Map([["m", history("marker")]])),
    ).toBeUndefined();
  });
});

describe("buildLiveChartView", () => {
  it("falls back (undefined) without an eligible numeric stream", () => {
    expect(buildLiveChartView(new Map(), undefined)).toBeUndefined();
    expect(
      buildLiveChartView(new Map([["m", history("marker")]]), undefined),
    ).toBeUndefined();
  });

  it("shows an empty history live with empty columns", () => {
    const view = buildLiveChartView(
      new Map([["s", history("numeric", ["a"], 0)]]),
      undefined,
    );
    expect(view?.data).toEqual([[], []]);
  });

  it("references history columns without copying, all channels included", () => {
    const h = history("eeg", ["a", "b", "c"]);
    const view = buildLiveChartView(new Map([["s", h]]), undefined);
    expect(view?.data).toHaveLength(4);
    expect(view?.data[0]).toBe(h.timestamps);
    h.values.forEach((column, i) => expect(view?.data[i + 1]).toBe(column));
    expect(view?.options.series.map((s) => s.label)).toEqual([
      "s time (s)",
      "a",
      "b",
      "c",
    ]);
  });

  it("reuses options for the same layout but builds a new outer array", () => {
    const h = history("numeric");
    const map = new Map([["s", h]]);
    const first = buildLiveChartView(map, undefined);
    h.timestamps.push(9);
    h.values.forEach((column) => column.push(9));
    const second = buildLiveChartView(map, first);
    expect(second?.options).toBe(first?.options);
    expect(second?.key).toBe(first?.key);
    expect(second?.data).not.toBe(first?.data);
  });

  it("builds new options and key on stream switch or layout change", () => {
    const map = new Map([["s", history("numeric")]]);
    const first = buildLiveChartView(map, undefined);
    map.set("s", history("numeric", ["a", "b", "c"]));
    const relaid = buildLiveChartView(map, first);
    expect(relaid?.options).not.toBe(first?.options);
    expect(relaid?.key).not.toBe(first?.key);
    map.set("eeg", history("eeg", ["a", "b", "c"]));
    const switched = buildLiveChartView(map, relaid);
    expect(switched?.name).toBe("eeg");
    expect(switched?.options).not.toBe(relaid?.options);
    expect(switched?.key).not.toBe(relaid?.key);
  });
});

describe("appendBounded", () => {
  it("keeps the newest rows within the limit", () => {
    const xs: number[] = [];
    const ys: number[] = [];
    appendBounded(
      xs,
      ys,
      [
        [0, 0],
        [1, 1],
        [2, 2],
      ],
      2,
    );
    appendBounded(xs, ys, [[3, 3]], 2);
    expect(xs).toEqual([2, 3]);
    expect(ys).toEqual([2, 3]);
  });
});
