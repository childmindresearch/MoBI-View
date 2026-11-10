/**
 * Page-local helpers that pick the live chart stream from `streamHistory`,
 * build uPlot data that reuses the history's column arrays, and keep chart
 * options stable until the selected stream or its channel layout changes.
 * Also holds the bounded synthetic preview used when no numeric stream exists.
 */

import type { AlignedData, Options } from "uplot";

import type { StreamHistories } from "$lib/stores/streams";
import { compareStreams } from "$lib/stream-classification";

/** Rows kept in the synthetic preview window. */
export const FALLBACK_SAMPLE_COUNT = 500;

/** Deterministic per-channel line colors, cycled when channels outnumber them. */
const SERIES_COLORS = [
  "#e6194b",
  "#3cb44b",
  "#4363d8",
  "#f58231",
  "#911eb4",
  "#42d4f4",
  "#f032e6",
  "#9a6324",
];

/** Chart view model for the selected live stream. */
export interface LiveChartView {
  /** Selected stream name. */
  name: string;
  /** Stream plus channel-layout identity; changes force a chart remount. */
  key: string;
  /** `[timestamps, ...values]`; a new outer array referencing history columns. */
  data: AlignedData;
  /** uPlot options, reused while `key` is unchanged. */
  options: Options;
}

/**
 * Picks the first EEG or numeric stream in display order; markers never chart.
 *
 * @param histories - Rolling history per stream.
 * @returns The selected stream name, or undefined when none is eligible.
 */
export function selectChartStream(
  histories: StreamHistories,
): string | undefined {
  let best: { name: string; category: "eeg" | "numeric" } | undefined;
  for (const [name, history] of histories) {
    if (history.category === "marker") continue;
    const candidate = { name, category: history.category };
    if (best === undefined || compareStreams(candidate, best) < 0) {
      best = candidate;
    }
  }
  return best?.name;
}

/**
 * Builds uPlot options for one stream layout, one series per channel.
 *
 * @param name - Stream name, used as the x-axis series label context.
 * @param labels - Channel labels, one series each.
 * @returns Fresh uPlot options.
 */
export function buildChartOptions(name: string, labels: string[]): Options {
  return {
    width: 760,
    height: 300,
    // LSL timestamps are sender seconds, not wall-clock dates.
    scales: { x: { time: false } },
    series: [
      { label: `${name} time (s)` },
      ...labels.map((label, i) => ({
        label,
        stroke: SERIES_COLORS[i % SERIES_COLORS.length],
        width: 1.5,
      })),
    ],
    axes: [{ label: "time (s)" }, { label: "amplitude" }],
    legend: { show: false },
  };
}

/**
 * Builds the live chart view, reusing the previous options when the stream
 * and channel layout are unchanged.
 *
 * @param histories - Rolling history per stream.
 * @param previous - The prior view, if any.
 * @returns The live view, or undefined when the synthetic fallback applies.
 */
export function buildLiveChartView(
  histories: StreamHistories,
  previous: LiveChartView | undefined,
): LiveChartView | undefined {
  const name = selectChartStream(histories);
  if (name === undefined) return undefined;
  const history = histories.get(name);
  if (history === undefined) return undefined;
  const labels = history.channel_labels;
  const key = JSON.stringify([name, labels]);
  const options =
    previous?.key === key ? previous.options : buildChartOptions(name, labels);
  return { name, key, data: [history.timestamps, ...history.values], options };
}

/**
 * Appends rows to the synthetic preview columns, trimming the oldest so each
 * column holds at most `limit` entries.
 *
 * @param xs - Sample-index column, mutated in place.
 * @param ys - Value column, mutated in place.
 * @param rows - `[x, y]` rows to append.
 * @param limit - Maximum retained rows.
 */
export function appendBounded(
  xs: number[],
  ys: number[],
  rows: [number, number][],
  limit: number = FALLBACK_SAMPLE_COUNT,
): void {
  for (const [x, y] of rows) {
    xs.push(x);
    ys.push(y);
  }
  const excess = xs.length - limit;
  if (excess > 0) {
    xs.splice(0, excess);
    ys.splice(0, excess);
  }
}
