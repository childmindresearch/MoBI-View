<!--
@component
MoBI-View dashboard page.

Connects to the backend WebSocket on mount. Charts the first EEG or numeric
stream, including empty retained histories; otherwise shows an empty-state
message. The sidebar and values panel list streams received since load.
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
    buildLiveChartView,
    chartEmptyMessage,
    type LiveChartView,
  } from "./chart-data";

  const status = websocketStore;

  /** Raw state keeps history columns outside Svelte's deep proxies. */
  let liveView = $state.raw<LiveChartView | undefined>(undefined);
  let emptyMessage = $state<string | undefined>("No stream found.");

  // Track only `revision`; the plain history Map is read untracked.
  $effect(() => {
    void $revision;
    untrack(() => {
      liveView = buildLiveChartView(streamHistory, liveView);
      emptyMessage = chartEmptyMessage(streamHistory);
    });
  });

  onMount(() => {
    websocketStore.connect();
  });

  onDestroy(() => {
    websocketStore.disconnect();
  });
</script>

<svelte:head>
  <title>MoBI-View</title>
  <meta
    name="description"
    content="MoBI-View browser frontend for real-time LSL stream visualization"
  />
</svelte:head>

<Sidebar.Provider>
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
        <Tabs.Content value="chart">
          <Card.Root
            class={liveView
              ? "w-fit"
              : "min-h-[300px] w-full max-w-[760px] min-w-0 items-center justify-center text-base leading-relaxed"}
          >
            {#if liveView}
              <Card.Header>
                <Card.Title>{liveView.name}</Card.Title>
                <Card.Description>Live stream</Card.Description>
              </Card.Header>
              <Card.Content>
                {#key liveView.key}
                  <UplotChart data={liveView.data} options={liveView.options} />
                {/key}
              </Card.Content>
            {:else}
              <Card.Header class="w-full text-center">
                <Card.Title class="leading-relaxed break-words">
                  {emptyMessage}
                </Card.Title>
              </Card.Header>
            {/if}
          </Card.Root>
        </Tabs.Content>

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
