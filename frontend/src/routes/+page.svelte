<!--
@component
MoBI-View dashboard.

Connects to the Python WebSocket server, keeps a rolling history for every
discovered LSL stream, and renders either a combined overview of all streams
or a focused full-size view of one stream.
-->
<script lang="ts">
  import { onDestroy, onMount } from "svelte";
  import ActivityIcon from "@lucide/svelte/icons/activity";
  import EyeIcon from "@lucide/svelte/icons/eye";
  import HeartPulseIcon from "@lucide/svelte/icons/heart-pulse";
  import LayoutGridIcon from "@lucide/svelte/icons/layout-grid";
  import RadioIcon from "@lucide/svelte/icons/radio";
  import RefreshCwIcon from "@lucide/svelte/icons/refresh-cw";
  import SearchIcon from "@lucide/svelte/icons/search";
  import Volume2Icon from "@lucide/svelte/icons/volume-2";
  import StreamPanel from "$lib/components/stream-panel.svelte";
  import { Button } from "$lib/components/ui/button/index.js";
  import * as Sidebar from "$lib/components/ui/sidebar/index.js";
  import { StreamStore } from "$lib/stream-store.svelte.js";
  import type { StreamState } from "$lib/stream-types.js";

  const store = new StreamStore();

  /** Selected view: `overview` or a stream name. */
  let activeView = $state("overview");
  /** Per-stream channel visibility, keyed by stream name. */
  let selection = $state<Record<string, boolean[]>>({});
  /** Per-stream stacked-view preference, keyed by stream name. */
  let stackedByStream = $state<Record<string, boolean>>({});

  const streams = $derived(store.streams);
  const eegStreams = $derived(streams.filter((stream) => stream.isEeg));
  const otherStreams = $derived(streams.filter((stream) => !stream.isEeg));

  const activeStream = $derived(
    streams.find((stream) => stream.name === activeView),
  );

  const totalChannels = $derived(
    streams.reduce((sum, stream) => sum + stream.labels.length, 0),
  );

  const statusLabel = $derived(
    store.status === "open"
      ? "Connected"
      : store.status === "connecting"
        ? "Connecting…"
        : "Disconnected",
  );

  // Give every newly discovered stream a default channel selection.
  $effect(() => {
    for (const stream of streams) {
      if (selection[stream.name] !== undefined) continue;
      selection[stream.name] = stream.labels.map(() => true);
      stackedByStream[stream.name] = stream.isEeg || stream.labels.length > 8;
    }
  });

  // Fall back to the overview if the focused stream disappears.
  $effect(() => {
    if (activeView === "overview") return;
    if (!streams.some((stream) => stream.name === activeView)) {
      activeView = "overview";
    }
  });

  onMount(() => store.connect());
  onDestroy(() => store.disconnect());

  /**
   * Toggles a single channel's visibility.
   *
   * @param name - Stream name owning the channel.
   * @param index - Channel index within the stream.
   */
  function toggleChannel(name: string, index: number): void {
    const flags = selection[name];
    if (flags === undefined) return;
    flags[index] = !flags[index];
  }

  /**
   * Shows or hides every channel of a stream.
   *
   * @param name - Stream name to update.
   * @param visible - Target visibility for all channels.
   */
  function setAllChannels(name: string, visible: boolean): void {
    const flags = selection[name];
    if (flags === undefined) return;
    selection[name] = flags.map(() => visible);
  }

  /**
   * Switches a stream between stacked and overlaid channel rendering.
   *
   * @param name - Stream name to update.
   */
  function toggleStacked(name: string): void {
    stackedByStream[name] = !stackedByStream[name];
  }

  /**
   * Counts the channels currently visible for a stream.
   *
   * @param stream - Stream to inspect.
   * @returns Number of enabled channels.
   */
  function visibleCount(stream: StreamState): number {
    return (selection[stream.name] ?? []).filter(Boolean).length;
  }
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
      <div class="brand">
        <span class="brand-mark"><ActivityIcon /></span>
        <span class="brand-text">
          <strong>MoBI-View</strong>
          <small>Real-time LSL</small>
        </span>
      </div>
    </Sidebar.Header>

    <Sidebar.Content>
      <Sidebar.Group>
        <Sidebar.GroupLabel>Dashboard</Sidebar.GroupLabel>
        <Sidebar.GroupContent>
          <Sidebar.Menu>
            <Sidebar.MenuItem>
              <Sidebar.MenuButton
                isActive={activeView === "overview"}
                onclick={() => (activeView = "overview")}
              >
                <LayoutGridIcon />
                <span>All streams</span>
              </Sidebar.MenuButton>
            </Sidebar.MenuItem>
          </Sidebar.Menu>
        </Sidebar.GroupContent>
      </Sidebar.Group>

      {#if eegStreams.length > 0}
        <Sidebar.Group>
          <Sidebar.GroupLabel>EEG</Sidebar.GroupLabel>
          <Sidebar.GroupContent>
            <Sidebar.Menu>
              {#each eegStreams as stream (stream.name)}
                <Sidebar.MenuItem>
                  <Sidebar.MenuButton
                    isActive={activeView === stream.name}
                    onclick={() => (activeView = stream.name)}
                  >
                    <ActivityIcon />
                    <span class="truncate">{stream.name}</span>
                  </Sidebar.MenuButton>
                  <Sidebar.MenuBadge>
                    {visibleCount(stream)}/{stream.labels.length}
                  </Sidebar.MenuBadge>
                </Sidebar.MenuItem>
              {/each}
            </Sidebar.Menu>
          </Sidebar.GroupContent>
        </Sidebar.Group>
      {/if}

      <Sidebar.Group>
        <Sidebar.GroupLabel>Streams</Sidebar.GroupLabel>
        <Sidebar.GroupContent>
          <Sidebar.Menu>
            {#each otherStreams as stream (stream.name)}
              <Sidebar.MenuItem>
                <Sidebar.MenuButton
                  isActive={activeView === stream.name}
                  onclick={() => (activeView = stream.name)}
                >
                  {#if stream.type.toLowerCase().includes("gaze")}
                    <EyeIcon />
                  {:else if stream.type.toLowerCase().includes("physio")}
                    <HeartPulseIcon />
                  {:else if stream.isMarker}
                    <Volume2Icon />
                  {:else}
                    <RadioIcon />
                  {/if}
                  <span class="truncate">{stream.name}</span>
                </Sidebar.MenuButton>
                {#if !stream.isMarker}
                  <Sidebar.MenuBadge>
                    {visibleCount(stream)}/{stream.labels.length}
                  </Sidebar.MenuBadge>
                {/if}
              </Sidebar.MenuItem>
            {:else}
              <p class="sidebar-empty">
                No streams yet. Start your LSL sources, then run Discover.
              </p>
            {/each}
          </Sidebar.Menu>
        </Sidebar.GroupContent>
      </Sidebar.Group>
    </Sidebar.Content>

    <Sidebar.Footer>
      <div class="conn" data-status={store.status}>
        <span class="conn-dot"></span>
        <span>{statusLabel}</span>
      </div>
    </Sidebar.Footer>
  </Sidebar.Root>

  <Sidebar.Inset>
    <header class="topbar">
      <div class="flex min-w-0 items-center gap-2">
        <Sidebar.Trigger />
        <div class="min-w-0">
          <h1 class="truncate">
            {activeStream ? activeStream.name : "All streams"}
          </h1>
          <p>
            {streams.length}
            {streams.length === 1 ? "stream" : "streams"} · {totalChannels} channels
          </p>
        </div>
      </div>

      <div class="flex shrink-0 items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          onclick={() => store.clearHistory()}
        >
          <RefreshCwIcon />
          Clear
        </Button>
        <Button
          size="sm"
          disabled={store.status !== "open" || store.discovering}
          onclick={() => store.discover()}
        >
          <SearchIcon />
          {store.discovering ? "Discovering…" : "Discover"}
        </Button>
      </div>
    </header>

    {#if store.lastError && store.status !== "open"}
      <p class="banner">{store.lastError}</p>
    {/if}

    <main class="content">
      {#if streams.length === 0}
        <div class="placeholder">
          <RadioIcon />
          <h2>No streams connected</h2>
          <p>
            Start your LSL outlets, then select <strong>Discover</strong> to pick
            them up without restarting the server.
          </p>
        </div>
      {:else if activeStream}
        <StreamPanel
          stream={activeStream}
          revision={store.revision}
          selected={selection[activeStream.name] ?? []}
          stacked={stackedByStream[activeStream.name] ?? false}
          onToggle={(index) => toggleChannel(activeStream.name, index)}
          onSetAll={(visible) => setAllChannels(activeStream.name, visible)}
          onToggleStacked={() => toggleStacked(activeStream.name)}
        />
      {:else}
        <div class="overview">
          {#each streams as stream (stream.name)}
            <div class:span-full={stream.isEeg}>
              <StreamPanel
                {stream}
                compact
                revision={store.revision}
                selected={selection[stream.name] ?? []}
                stacked={stackedByStream[stream.name] ?? false}
                onToggle={(index) => toggleChannel(stream.name, index)}
                onSetAll={(visible) => setAllChannels(stream.name, visible)}
                onToggleStacked={() => toggleStacked(stream.name)}
              />
            </div>
          {/each}
        </div>
      {/if}
    </main>
  </Sidebar.Inset>
</Sidebar.Provider>

<style>
  .brand {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    padding: 0.35rem 0.4rem;
  }

  .brand-mark {
    display: grid;
    width: 2rem;
    height: 2rem;
    place-items: center;
    border-radius: 8px;
    background: var(--sidebar-primary);
    color: var(--sidebar-primary-foreground);
  }

  .brand-mark :global(svg) {
    width: 1rem;
    height: 1rem;
  }

  .brand-text {
    display: grid;
    line-height: 1.2;
  }

  .brand-text strong {
    font-size: 0.9rem;
  }

  .brand-text small {
    color: color-mix(in oklab, var(--sidebar-foreground) 65%, transparent);
    font-size: 0.68rem;
  }

  .sidebar-empty {
    padding: 0.3rem 0.55rem;
    color: color-mix(in oklab, var(--sidebar-foreground) 65%, transparent);
    font-size: 0.72rem;
    line-height: 1.45;
  }

  .conn {
    display: flex;
    align-items: center;
    gap: 0.45rem;
    padding: 0.4rem 0.55rem;
    font-size: 0.72rem;
    font-weight: 600;
  }

  .conn-dot {
    width: 0.5rem;
    height: 0.5rem;
    border-radius: 50%;
    background: var(--muted-foreground);
  }

  .conn[data-status="open"] .conn-dot {
    background: var(--chart-3);
    box-shadow: 0 0 0 3px color-mix(in oklab, var(--chart-3) 22%, transparent);
  }

  .conn[data-status="connecting"] .conn-dot {
    background: var(--chart-4);
  }

  .conn[data-status="closed"] .conn-dot {
    background: var(--destructive);
  }

  .topbar {
    display: flex;
    position: sticky;
    z-index: 10;
    top: 0;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    padding: 0.7rem 1.25rem;
    border-bottom: 1px solid var(--border);
    background: color-mix(in oklab, var(--background) 88%, transparent);
    backdrop-filter: blur(8px);
  }

  .topbar h1 {
    font-size: 0.95rem;
    font-weight: 650;
  }

  .topbar p {
    color: var(--muted-foreground);
    font-size: 0.72rem;
  }

  .banner {
    padding: 0.55rem 1.25rem;
    border-bottom: 1px solid var(--border);
    background: color-mix(in oklab, var(--destructive) 12%, var(--background));
    color: var(--destructive);
    font-size: 0.76rem;
  }

  .content {
    flex: 1;
    padding: 1.25rem;
    background: color-mix(in oklab, var(--muted) 40%, var(--background));
  }

  .overview {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(min(100%, 420px), 1fr));
    gap: 1.25rem;
    align-items: start;
  }

  .span-full {
    grid-column: 1 / -1;
  }

  .placeholder {
    display: grid;
    justify-items: center;
    max-width: 26rem;
    margin: 5rem auto;
    gap: 0.5rem;
    text-align: center;
  }

  .placeholder :global(svg) {
    width: 2rem;
    height: 2rem;
    color: var(--muted-foreground);
  }

  .placeholder h2 {
    font-size: 1rem;
    font-weight: 650;
  }

  .placeholder p {
    color: var(--muted-foreground);
    font-size: 0.82rem;
    line-height: 1.5;
  }
</style>
