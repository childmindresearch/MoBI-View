<!--
@component
Thin Svelte wrapper around a uPlot chart instance.

Builds the chart when mounted and rebuilds it (destroying the old instance)
whenever `options` is replaced. `data` changes are pushed into the existing
instance via `setData` without a rebuild. Width tracks the container
(minimum 240px); height always comes from the current `options.height`.
-->
<script lang="ts">
  import { untrack } from "svelte";
  import uPlot, { type Options } from "uplot";
  import "uplot/dist/uPlot.min.css";

  /**
   * Props accepted by the chart wrapper.
   *
   * @property data - Column-oriented series data (`[xs, ys, ...]`).
   * @property options - uPlot configuration (size, scales, series, axes).
   * @property class - Optional CSS class applied to the container element.
   */
  type Props = {
    data: uPlot.AlignedData;
    options: Options;
    class?: string;
  };

  /** Smallest width, in pixels, the chart is ever sized to. */
  const MIN_WIDTH = 240;

  let { data, options, class: className = "" }: Props = $props();

  /** Container element the uPlot instance renders into. */
  let container: HTMLDivElement | undefined = $state();
  /** Active uPlot instance; deliberately non-reactive to avoid rebuild loops. */
  let chart: uPlot | undefined;
  /** Data last handed to `chart`, so construction is not followed by a redundant `setData`. */
  let appliedData: uPlot.AlignedData | undefined;

  /**
   * Clamps a measured container width to the chart minimum.
   *
   * @param width - Measured width in pixels.
   * @returns Width no smaller than `MIN_WIDTH`.
   */
  function clampWidth(width: number): number {
    return Math.max(MIN_WIDTH, Math.floor(width));
  }

  // Rebuild only when options or the container change; data is read untracked.
  $effect(() => {
    const opts = options;
    const target = container;
    if (!target) return;

    // Zero width (not laid out yet) falls back to the configured width.
    const instance = untrack(() => {
      appliedData = data;
      return new uPlot(
        { ...opts, width: clampWidth(target.clientWidth || opts.width) },
        data,
        target,
      );
    });
    chart = instance;
    let active = true;

    const observer = new ResizeObserver((entries) => {
      if (!active) return;
      const width = entries[entries.length - 1]?.contentRect.width ?? 0;
      instance.setSize({ width: clampWidth(width), height: opts.height });
    });
    observer.observe(target);

    return () => {
      active = false;
      observer.disconnect();
      instance.destroy();
      if (chart === instance) chart = undefined;
    };
  });

  $effect(() => {
    const next = data;
    untrack(() => {
      if (!chart || next === appliedData) return;
      appliedData = next;
      chart.setData(next);
    });
  });
</script>

<div bind:this={container} class={className}></div>
