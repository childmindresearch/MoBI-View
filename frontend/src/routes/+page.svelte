<!--
@component
MoBI-View dashboard page.

Auto-connects to the backend WebSocket on mount and renders live LSL stream
values from the broadcast data frames. The uPlot chart still shows a synthetic
preview signal; the sidebar and the values panel reflect real stream data.
-->
<script lang="ts">
  import { onDestroy, onMount } from "svelte";
  import { ScrollArea } from "$lib/components/ui/scroll-area/index.js";
  import * as Tabs from "$lib/components/ui/tabs/index.js";
  import * as Sidebar from "$lib/components/ui/sidebar/index.js";
  import * as Card from "$lib/components/ui/card/index.js";
  import { Button } from "$lib/components/ui/button/index.js";
  import UplotChart from "$lib/components/uplot-chart.svelte";
  import { websocketStore } from "$lib/stores/websocket";
  import { discoveredStreams, streamSamples } from "$lib/stores/streams";
  import type { Options, AlignedData } from "uplot";

  /** Live WebSocket connection status, driven by the connection store. */
  const status = websocketStore;

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
    websocketStore.connect();

    for (let i = 0; i < sampleCount; i += 1) pushSample();
    updateWindow();

    timer = setInterval(() => {
      for (let i = 0; i < stepSize; i += 1) pushSample();
      updateWindow();
    }, tickMs);
  });

  onDestroy(() => {
    if (timer !== undefined) clearInterval(timer);
    websocketStore.disconnect();
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
  <!-- Sidebar lists the streams currently sending data frames. -->
  <Sidebar.Root>
    <Sidebar.Header>
      <span class="px-2 py-1 text-sm font-semibold">MoBI-View</span>
    </Sidebar.Header>
    <Sidebar.Content>
      <Sidebar.Group>
        <Sidebar.GroupLabel>Streams</Sidebar.GroupLabel>
        <Sidebar.GroupContent>
          <Sidebar.Menu>
            {#each Object.values($streamSamples) as stream (stream.stream_name)}
              <Sidebar.MenuItem>
                <Sidebar.MenuButton>{stream.stream_name}</Sidebar.MenuButton>
              </Sidebar.MenuItem>
            {:else}
              <span class="text-muted-foreground px-2 py-1 text-xs">
                No active streams
              </span>
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

        <div class="ml-auto flex items-center gap-3">
          {#if $discoveredStreams.length > 0}
            <span class="text-xs text-muted-foreground">
              Discovered: {$discoveredStreams.join(", ")}
            </span>
          {/if}
          <span class="text-xs text-muted-foreground">{$status}</span>
          <Button
            size="sm"
            variant="outline"
            onclick={() => websocketStore.reconnect()}
          >
            Reconnect
          </Button>
          <Button size="sm" onclick={() => websocketStore.sendDiscover()}>
            Discover
          </Button>
        </div>
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

        <!-- Live stream values from the backend broadcast data frames. -->
        <Tabs.Content value="channels">
          <ScrollArea class="h-96 w-full max-w-2xl rounded-md border">
            <div class="flex flex-col gap-4 p-4">
              {#each Object.values($streamSamples) as stream (stream.stream_name)}
                <div>
                  <div class="mb-1 text-sm font-semibold">
                    {stream.stream_name}
                  </div>
                  <div
                    class="grid grid-cols-2 gap-x-4 gap-y-1 font-mono text-xs sm:grid-cols-3"
                  >
                    {#each stream.channel_labels as label, i (i)}
                      <div class="flex justify-between gap-2">
                        <span class="text-muted-foreground">{label}</span>
                        <span>{stream.data[i]?.toFixed(3) ?? "—"}</span>
                      </div>
                    {/each}
                  </div>
                </div>
              {:else}
                <span class="text-muted-foreground text-sm">
                  Waiting for stream data…
                </span>
              {/each}
            </div>
          </ScrollArea>
        </Tabs.Content>
      </div>
    </Tabs.Root>
  </Sidebar.Inset>
</Sidebar.Provider>
