<!--
@component
Thin Svelte wrapper around a uPlot chart instance.

Owns the uPlot lifecycle: rebuilds the chart when `options` change (series
or axis configuration), pushes new samples into the existing instance when
only `data` changes, and keeps the canvas sized to its container.
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

  let { data, options, class: className = "" }: Props = $props();

  /** Minimum canvas width, guarding against zero-width layout passes. */
  const MIN_WIDTH = 240;

  /** Container element the uPlot instance renders into. */
  let container: HTMLDivElement;
  /** Active uPlot instance; undefined before the first effect run. */
  let chart: uPlot | undefined;

  $effect(() => {
    const nextOptions = options;
    if (!container) return;

    const instance = new uPlot(
      {
        ...nextOptions,
        width: Math.max(MIN_WIDTH, Math.floor(container.clientWidth)),
      },
      untrack(() => data),
      container,
    );
    chart = instance;

    const observer = new ResizeObserver(([entry]) => {
      const width = Math.floor(entry.contentRect.width);
      if (width === 0) return;
      instance.setSize({
        width: Math.max(MIN_WIDTH, width),
        height: nextOptions.height,
      });
    });
    observer.observe(container);

    return () => {
      observer.disconnect();
      instance.destroy();
      if (chart === instance) chart = undefined;
    };
  });

  $effect(() => {
    const nextData = data;
    untrack(() => chart)?.setData(nextData);
  });
</script>

<div bind:this={container} class={`w-full ${className}`}></div>
