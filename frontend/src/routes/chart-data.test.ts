/** Tests for the page-local live chart selection, data, and options helpers. */

import { describe, expect, it } from "vitest";

import type { StreamHistory } from "$lib/stores/streams";
import type { StreamCategory } from "$lib/stream-classification";

import {
  buildLiveChartView,
  chartEmptyMessage,
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
    map.set("aeeg", history("eeg"));
    expect(selectChartStream(map)).toBe("aeeg");
  });

  it("returns undefined for an empty map or markers only", () => {
    expect(selectChartStream(new Map())).toBeUndefined();
    expect(
      selectChartStream(new Map([["m", history("marker")]])),
    ).toBeUndefined();
  });
});

describe("chartEmptyMessage", () => {
  it("distinguishes no streams from marker-only histories", () => {
    expect(chartEmptyMessage(new Map())).toBe("No stream found.");
    expect(chartEmptyMessage(new Map([["m", history("marker")]]))).toBe(
      "No numeric stream available to chart.",
    );
  });

  it("stops showing an empty message when the first numeric stream arrives", () => {
    const map = new Map<string, StreamHistory>();
    expect(chartEmptyMessage(map)).toBe("No stream found.");
    expect(buildLiveChartView(map, undefined)).toBeUndefined();
    map.set("s", history("numeric"));
    expect(chartEmptyMessage(map)).toBeUndefined();
    expect(buildLiveChartView(map, undefined)?.name).toBe("s");
  });

  it("follows category changes between marker and numeric", () => {
    const h = history("marker", ["a"], 0);
    const map = new Map([["s", h]]);
    expect(buildLiveChartView(map, undefined)).toBeUndefined();
    expect(chartEmptyMessage(map)).toBe(
      "No numeric stream available to chart.",
    );

    h.category = "numeric";
    const live = buildLiveChartView(map, undefined);
    expect(live?.name).toBe("s");
    expect(chartEmptyMessage(map)).toBeUndefined();

    h.category = "marker";
    expect(buildLiveChartView(map, live)).toBeUndefined();
    expect(chartEmptyMessage(map)).toBe(
      "No numeric stream available to chart.",
    );
  });
});

describe("buildLiveChartView", () => {
  it("returns undefined without an eligible numeric stream", () => {
    expect(buildLiveChartView(new Map(), undefined)).toBeUndefined();
    expect(
      buildLiveChartView(new Map([["m", history("marker")]]), undefined),
    ).toBeUndefined();
  });

  it("shows an empty history live with empty columns", () => {
    const map = new Map([["s", history("numeric", ["a"], 0)]]);
    const view = buildLiveChartView(map, undefined);
    expect(view?.name).toBe("s");
    expect(view?.data).toEqual([[], []]);
    expect(chartEmptyMessage(map)).toBeUndefined();
  });

  it("keeps the live chart identity when retained history is cleared", () => {
    const h = history("numeric");
    const map = new Map([["s", h]]);
    const first = buildLiveChartView(map, undefined);
    h.timestamps.length = 0;
    h.values.forEach((column) => (column.length = 0));
    const cleared = buildLiveChartView(map, first);
    expect(cleared?.name).toBe("s");
    expect(cleared?.data).toEqual([[], [], []]);
    expect(cleared?.options).toBe(first?.options);
    expect(cleared?.key).toBe(first?.key);
    expect(chartEmptyMessage(map)).toBeUndefined();
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
    expect(second?.data[0]).toBe(h.timestamps);
    h.values.forEach((column, i) => expect(second?.data[i + 1]).toBe(column));
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
