<!--
@component
MoBI-View dashboard page.

Everything on this page is a placeholder demo: the sidebar entries, the
channel list, and the chart data are synthetic stand-ins until real LSL
stream data is wired in over the WebSocket connection.
-->
<script lang="ts">
  import { onDestroy, onMount } from "svelte";
  import { ScrollArea } from "$lib/components/ui/scroll-area/index.js";
  import * as Tabs from "$lib/components/ui/tabs/index.js";
  import * as Sidebar from "$lib/components/ui/sidebar/index.js";
  import * as Card from "$lib/components/ui/card/index.js";
  import UplotChart from "$lib/components/uplot-chart.svelte";
  import type { Options, AlignedData } from "uplot";

  /** Placeholder channel names; will come from discovered LSL streams. */
  const channels = Array.from(
    { length: 30 },
    (_, index) => `Channel ${index + 1}`,
  );

  /** Number of samples kept in the visible sliding window. */
  const sampleCount = 500;
  /** Samples appended per timer tick. */
  const stepSize = 2;
  /** Timer tick period in milliseconds (~30 fps). */
  const tickMs = 33;
  /** Backing stores for the full synthetic stream (x = sample index). */
  const streamX: number[] = [];
  const streamY: number[] = [];

  /** Windowed data currently shown by the chart. */
  let data = $state<AlignedData>([[], []]);
  let tick = 0;
  let timer: ReturnType<typeof setInterval> | undefined;

  /**
   * Generates one placeholder signal sample.
   *
   * @param t - Sample index.
   * @returns Synthetic waveform value: two sines plus light noise.
   */
  function sample(t: number): number {
    return (
      Math.sin(t / 10) + 0.25 * Math.sin(t / 3) + 0.1 * (Math.random() - 0.5)
    );
  }

  /** Appends the next synthetic sample to the stream buffers. */
  function pushSample(): void {
    streamX.push(tick);
    streamY.push(sample(tick));
    tick += 1;
  }

  /**
   * Returns a windowed copy of the stream in uPlot's aligned-data layout.
   *
   * @param start - Inclusive start index.
   * @param end - Exclusive end index.
   * @returns `[xs, ys]` slices for the requested range.
   */
  function sliceData(start: number, end: number): AlignedData {
    return [streamX.slice(start, end), streamY.slice(start, end)];
  }

  /** Advances the visible window to the latest `sampleCount` samples. */
  function updateWindow(): void {
    const end = streamX.length;
    const start = Math.max(0, end - sampleCount);
    data = sliceData(start, end);
  }

  onMount(() => {
    for (let i = 0; i < sampleCount; i += 1) pushSample();
    updateWindow();

    timer = setInterval(() => {
      for (let i = 0; i < stepSize; i += 1) pushSample();
      updateWindow();
    }, tickMs);
  });

  onDestroy(() => {
    if (timer !== undefined) clearInterval(timer);
  });

  /** Placeholder chart configuration for the single demo series. */
  const options: Options = {
    width: 760,
    height: 300,
    scales: { x: { time: false } },
    series: [
      { label: "sample" },
      { label: "Channel 1", stroke: "red", width: 1.5 },
    ],
    axes: [{ label: "sample" }, { label: "amplitude" }],
    legend: { show: false },
  };
</script>

<svelte:head>
  <title>MoBI-View</title>
  <meta
    name="description"
    content="MoBI-View browser frontend for real-time LSL stream visualization"
  />
</svelte:head>

<Sidebar.Provider>
  <!-- Placeholder sidebar: lists the first few fake channels as stand-ins
       for discovered LSL streams. -->
  <Sidebar.Root>
    <Sidebar.Header>
      <span class="px-2 py-1 text-sm font-semibold">MoBI-View</span>
    </Sidebar.Header>
    <Sidebar.Content>
      <Sidebar.Group>
        <Sidebar.GroupLabel>Streams</Sidebar.GroupLabel>
        <Sidebar.GroupContent>
          <Sidebar.Menu>
            {#each channels.slice(0, 5) as channel (channel)}
              <Sidebar.MenuItem>
                <Sidebar.MenuButton>{channel}</Sidebar.MenuButton>
              </Sidebar.MenuItem>
            {/each}
          </Sidebar.Menu>
        </Sidebar.GroupContent>
      </Sidebar.Group>
    </Sidebar.Content>
  </Sidebar.Root>

  <Sidebar.Inset>
    <Tabs.Root value="chart" class="flex flex-1 flex-col">
      <header
        class="flex items-center gap-2 border-b px-4 py-3 text-sm font-medium"
      >
        <Sidebar.Trigger />
        <span>Dashboard</span>
        <Tabs.List aria-label="MoBI-View dashboard tabs" class="ml-4">
          <Tabs.Trigger value="chart">Chart</Tabs.Trigger>
          <Tabs.Trigger value="channels">Channels</Tabs.Trigger>
        </Tabs.List>
      </header>

      <div class="flex flex-col gap-6 bg-background p-6 text-foreground">
        <!-- Placeholder chart: synthetic looping waveform, not live LSL data. -->
        <Tabs.Content value="chart">
          <Card.Root class="w-fit">
            <Card.Header>
              <Card.Title>Channel 1</Card.Title>
              <Card.Description>Synthetic preview signal</Card.Description>
            </Card.Header>
            <Card.Content>
              <UplotChart {data} {options} />
            </Card.Content>
          </Card.Root>
        </Tabs.Content>

        <!-- Placeholder channel list: static names until real metadata arrives. -->
        <Tabs.Content value="channels">
          <ScrollArea class="h-50 w-50 rounded-md border">
            <div class="p-4">
              {#each channels as channel (channel)}
                <div class="text-sm">{channel}</div>
              {/each}
            </div>
          </ScrollArea>
        </Tabs.Content>
      </div>
    </Tabs.Root>
  </Sidebar.Inset>
</Sidebar.Provider>
