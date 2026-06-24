<!--
@component
Thin Svelte wrapper around a uPlot chart instance.

Owns the uPlot lifecycle: creates the chart on mount, destroys it on
unmount, and pushes new data into the existing instance whenever the
`data` prop changes.
-->
<script lang="ts">
  import { onDestroy, onMount } from "svelte";
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

  /** Container element the uPlot instance renders into. */
  let container: HTMLDivElement;
  /** Active uPlot instance; undefined until mounted. */
  let chart: uPlot | undefined;

  onMount(() => {
    chart = new uPlot(options, data, container);
  });

  onDestroy(() => {
    chart?.destroy();
  });

  $effect(() => {
    chart?.setData(data);
  });
</script>

<div bind:this={container} class={className}></div>
