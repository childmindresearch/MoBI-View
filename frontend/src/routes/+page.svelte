<script lang="ts">
  import { onDestroy, onMount } from "svelte";
  import { ScrollArea } from "$lib/components/ui/scroll-area/index.js";
  import * as Tabs from "$lib/components/ui/tabs/index.js";
  import * as Sidebar from "$lib/components/ui/sidebar/index.js";
  import * as Card from "$lib/components/ui/card/index.js";
  import UplotChart from "$lib/components/uplot-chart.svelte";
  import type { Options, AlignedData } from "uplot";

  const channels = Array.from(
    { length: 30 },
    (_, index) => `Channel ${index + 1}`,
  );

  const sampleCount = 500;
  const stepSize = 2;
  const tickMs = 33;
  const streamX: number[] = [];
  const streamY: number[] = [];

  let data = $state<AlignedData>([[], []]);
  let tick = 0;
  let timer: ReturnType<typeof setInterval> | undefined;

  function sample(t: number): number {
    return (
      Math.sin(t / 10) + 0.25 * Math.sin(t / 3) + 0.1 * (Math.random() - 0.5)
    );
  }

  function pushSample(): void {
    streamX.push(tick);
    streamY.push(sample(tick));
    tick += 1;
  }

  function sliceData(start: number, end: number): AlignedData {
    return [streamX.slice(start, end), streamY.slice(start, end)];
  }

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
