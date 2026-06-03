<script lang="ts">
  import { onDestroy, onMount } from "svelte";
  import uPlot, { type Options } from "uplot";
  import "uplot/dist/uPlot.min.css";

  type Props = {
    data: uPlot.AlignedData;
    options: Options;
    class?: string;
  };

  let { data, options, class: className = "" }: Props = $props();

  let container: HTMLDivElement;
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
