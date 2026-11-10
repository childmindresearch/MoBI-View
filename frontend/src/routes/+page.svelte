<!--
@component
MoBI-View dashboard page.

Auto-connects to the backend WebSocket on mount and renders live LSL stream
values from the broadcast data frames. The uPlot chart shows the first EEG or
numeric stream, or a synthetic preview signal when none exists; the sidebar and the values panel list every stream seen since
load, with each stream's latest received batch.
-->
<script lang="ts">
  import { onDestroy, onMount, untrack } from "svelte";
  import { ScrollArea } from "$lib/components/ui/scroll-area/index.js";
  import * as Tabs from "$lib/components/ui/tabs/index.js";
  import * as Sidebar from "$lib/components/ui/sidebar/index.js";
  import * as Card from "$lib/components/ui/card/index.js";
  import { Button } from "$lib/components/ui/button/index.js";
  import UplotChart from "$lib/components/uplot-chart.svelte";
  import { websocketStore } from "$lib/stores/websocket";
  import {
    discoveredStreams,
    orderedStreams,
    revision,
    streamHistory,
  } from "$lib/stores/streams";
  import {
    appendBounded,
    buildLiveChartView,
    FALLBACK_SAMPLE_COUNT,
    type LiveChartView,
  } from "./chart-data";
  import type { Options, AlignedData } from "uplot";

  /** Live WebSocket connection status, driven by the connection store. */
  const status = websocketStore;

  /** Samples appended per synthetic preview tick. */
  const stepSize = 2;
  /** Synthetic preview tick period in milliseconds (~30 fps). */
  const tickMs = 33;
  /** Bounded synthetic preview columns (x = sample index). */
  const streamX: number[] = [];
  const streamY: number[] = [];
  let tick = 0;

  /** Synthetic preview data, shown only while no numeric stream is live. */
  let fallbackData = $state.raw<AlignedData>([[], []]);
  /**
   * Live chart view; raw state so history columns never become deep proxies.
   */
  let liveView = $state.raw<LiveChartView | undefined>(undefined);

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

  /**
   * Appends synthetic rows within the bounded window and republishes them.
   *
   * @param count - Rows to append.
   */
  function advanceFallback(count: number): void {
    const rows: [number, number][] = [];
    for (let i = 0; i < count; i += 1) {
      rows.push([tick, sample(tick)]);
      tick += 1;
    }
    appendBounded(streamX, streamY, rows, FALLBACK_SAMPLE_COUNT);
    fallbackData = [streamX, streamY];
  }

  // Track only `revision`; the plain history Map is read untracked.
  $effect(() => {
    void $revision;
    untrack(() => {
      liveView = buildLiveChartView(streamHistory, liveView);
    });
  });

  const isLive = $derived(liveView !== undefined);

  // Run the synthetic preview timer only while no live stream is charted.
  $effect(() => {
    if (isLive) return;
    untrack(() => {
      if (streamX.length === 0) advanceFallback(FALLBACK_SAMPLE_COUNT);
    });
    const timer = setInterval(() => advanceFallback(stepSize), tickMs);
    return () => clearInterval(timer);
  });

  onMount(() => {
    websocketStore.connect();
  });

  onDestroy(() => {
    websocketStore.disconnect();
  });

  /** Placeholder chart configuration for the single demo series. */
  const fallbackOptions: Options = {
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
  <!-- Sidebar lists every stream seen in a data frame since load, in display order; quiet streams stay listed. -->
  <Sidebar.Root>
    <Sidebar.Header>
      <span class="px-2 py-1 text-sm font-semibold">MoBI-View</span>
    </Sidebar.Header>
    <Sidebar.Content>
      <Sidebar.Group>
        <Sidebar.GroupLabel>Streams</Sidebar.GroupLabel>
        <Sidebar.GroupContent>
          <Sidebar.Menu>
            {#each $orderedStreams as stream (stream.stream_name)}
              <Sidebar.MenuItem>
                <Sidebar.MenuButton>{stream.stream_name}</Sidebar.MenuButton>
              </Sidebar.MenuItem>
            {:else}
              <span class="text-muted-foreground px-2 py-1 text-xs">
                No streams seen yet
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
        <!-- Live chart of the selected stream, or a synthetic preview. -->
        <Tabs.Content value="chart">
          <Card.Root class="w-fit">
            {#if liveView}
              <Card.Header>
                <Card.Title>{liveView.name}</Card.Title>
                <Card.Description>Live stream</Card.Description>
              </Card.Header>
              <Card.Content>
                <!-- Remount only when the stream or channel layout changes. -->
                {#key liveView.key}
                  <UplotChart data={liveView.data} options={liveView.options} />
                {/key}
              </Card.Content>
            {:else}
              <Card.Header>
                <Card.Title>Channel 1</Card.Title>
                <Card.Description>Synthetic preview signal</Card.Description>
              </Card.Header>
              <Card.Content>
                <UplotChart data={fallbackData} options={fallbackOptions} />
              </Card.Content>
            {/if}
          </Card.Root>
        </Tabs.Content>

        <!-- Live stream values from the backend broadcast data frames. -->
        <Tabs.Content value="channels">
          <ScrollArea class="h-96 w-full max-w-2xl rounded-md border">
            <div class="flex flex-col gap-4 p-4">
              {#each $orderedStreams as stream (stream.stream_name)}
                {@const latest = stream.samples.at(-1)}
                <div>
                  <div class="mb-1 text-sm font-semibold">
                    {stream.stream_name}
                  </div>
                  <div
                    class="grid grid-cols-2 gap-x-4 gap-y-1 font-mono text-xs sm:grid-cols-3"
                  >
                    {#each stream.channel_labels as label, i (i)}
                      {@const value = latest?.[i]}
                      <div class="flex justify-between gap-2">
                        <span class="text-muted-foreground">{label}</span>
                        <span>
                          {typeof value === "number"
                            ? value.toFixed(3)
                            : (value ?? "—")}
                        </span>
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
