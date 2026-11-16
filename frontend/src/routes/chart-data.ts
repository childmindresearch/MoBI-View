/**
 * Page-local helpers that pick the live chart stream from `streamHistory`,
 * build uPlot data that reuses the history's column arrays, and keep chart
 * options stable until the selected stream or its channel layout changes.
 */

import type { AlignedData, Options } from "uplot";

import type { StreamHistories } from "$lib/stores/streams";
import { compareStreams } from "$lib/stream-classification";

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

/**
 * Live view with a remount key for stream/layout changes, a new outer data
 * array referencing raw history columns, and options reused while the key holds.
 */
export interface LiveChartView {
  name: string;
  key: string;
  data: AlignedData;
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
 * Distinguishes absent streams from histories with no chartable stream.
 *
 * @param histories - Rolling history per stream.
 * @returns The empty-state message, or undefined when a numeric stream exists.
 */
export function chartEmptyMessage(
  histories: StreamHistories,
): string | undefined {
  if (histories.size === 0) return "No stream found.";
  return selectChartStream(histories) === undefined
    ? "No numeric stream available to chart."
    : undefined;
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
 * @returns The live view, or undefined when no numeric stream exists.
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
