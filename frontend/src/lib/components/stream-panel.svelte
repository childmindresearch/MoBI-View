<!--
@component
Live view of a single LSL stream: chart or marker feed, latest readings,
and per-channel visibility toggles.

Numeric streams are plotted with uPlot. Streams with many channels (EEG)
default to a stacked view where each channel is drawn on its own baseline.
Marker streams carry no plottable values, so they render an event feed.
-->
<script lang="ts">
  import ActivityIcon from "@lucide/svelte/icons/activity";
  import CheckCheckIcon from "@lucide/svelte/icons/list-checks";
  import EyeIcon from "@lucide/svelte/icons/eye";
  import HeartPulseIcon from "@lucide/svelte/icons/heart-pulse";
  import LayersIcon from "@lucide/svelte/icons/layers";
  import RadioIcon from "@lucide/svelte/icons/radio";
  import SquareXIcon from "@lucide/svelte/icons/square-x";
  import Volume2Icon from "@lucide/svelte/icons/volume-2";
  import type { AlignedData, Options, Series } from "uplot";
  import UplotChart from "$lib/components/uplot-chart.svelte";
  import { Button } from "$lib/components/ui/button/index.js";
  import * as Card from "$lib/components/ui/card/index.js";
  import { CHANNEL_COLORS } from "$lib/stream-colors.js";
  import type { StreamState } from "$lib/stream-types.js";

  /**
   * Props accepted by the stream panel.
   *
   * @property stream - Non-reactive history container for this stream.
   * @property revision - Counter bumped when new samples arrive; read to
   *   recompute derived values without proxying the history arrays.
   * @property selected - Per-channel visibility flags, indexed like `labels`.
   * @property compact - Renders the denser overview variant.
   * @property stacked - Draws each channel on its own baseline.
   * @property onToggle - Toggles visibility of a single channel.
   * @property onSetAll - Shows or hides every channel at once.
   * @property onToggleStacked - Switches between stacked and overlaid views.
   */
  type Props = {
    stream: StreamState;
    revision: number;
    selected: boolean[];
    compact?: boolean;
    stacked?: boolean;
    onToggle: (index: number) => void;
    onSetAll: (visible: boolean) => void;
    onToggleStacked?: () => void;
  };

  let {
    stream,
    revision,
    selected,
    compact = false,
    stacked = false,
    onToggle,
    onSetAll,
    onToggleStacked,
  }: Props = $props();

  /**
   * Baselines and labels for the stacked y-axis.
   *
   * uPlot options must stay referentially stable or the chart is rebuilt on
   * every frame, so the axis reads these through a mutable holder that the
   * data derivation updates in place.
   */
  const stackLayout = { offsets: [] as number[], labels: [] as string[] };

  const visibleIndices = $derived(
    selected.flatMap((isVisible, index) => (isVisible ? [index] : [])),
  );

  const chartHeight = $derived(compact ? 260 : stacked ? 560 : 420);

  const effectiveRate = $derived.by(() => {
    void revision;
    const span = stream.lastTimestamp - stream.firstTimestamp;
    if (span <= 0 || stream.sampleCount < 2) return 0;
    return (stream.sampleCount - 1) / span;
  });

  const latest = $derived.by(() => {
    void revision;
    return stream.latest;
  });

  const markerFeed = $derived.by(() => {
    void revision;
    return stream.markers.slice(compact ? -6 : -14).reverse();
  });

  const hasSamples = $derived.by(() => {
    void revision;
    return stream.timestamps.length > 0;
  });

  const chartData = $derived.by((): AlignedData => {
    void revision;
    const xs = stream.timestamps;
    const columns = visibleIndices.map((index) => stream.values[index] ?? []);

    if (!stacked || columns.length === 0) {
      stackLayout.offsets = [];
      stackLayout.labels = [];
      return [xs, ...columns] as AlignedData;
    }

    const spacing = stackSpacing(columns);
    const offsets: number[] = [];
    const labels: string[] = [];
    const stackedColumns = columns.map((column, position) => {
      // Draw the first selected channel at the top of the stack.
      const offset = (columns.length - 1 - position) * spacing;
      offsets.push(offset);
      labels.push(stream.labels[visibleIndices[position]] ?? "");

      const shifted = new Float64Array(column.length);
      for (let i = 0; i < column.length; i += 1) shifted[i] = column[i] + offset;
      return shifted;
    });

    stackLayout.offsets = offsets;
    stackLayout.labels = labels;
    return [xs, ...stackedColumns] as AlignedData;
  });

  const chartOptions = $derived.by((): Options => {
    const series: Series[] = [
      { label: "Time" },
      ...visibleIndices.map((index) => ({
        label: stream.labels[index] ?? `Channel ${index + 1}`,
        stroke: CHANNEL_COLORS[index % CHANNEL_COLORS.length],
        width: stacked ? 1 : 1.6,
        points: { show: false },
      })),
    ];

    return {
      width: 900,
      height: chartHeight,
      series,
      scales: { x: { time: false } },
      axes: [
        {
          stroke: "#5c6b76",
          grid: { stroke: "#e3eaee", width: 1 },
          ticks: { stroke: "#c3ced5" },
          values: (_chart, splits, _axisIndex, _space, incr) =>
            splits.map((value) => formatElapsed(value, incr)),
        },
        stacked
          ? {
              stroke: "#5c6b76",
              grid: { show: false },
              ticks: { stroke: "#c3ced5" },
              size: 66,
              splits: () => stackLayout.offsets,
              values: () => stackLayout.labels,
            }
          : {
              stroke: "#5c6b76",
              grid: { stroke: "#edf2f4", width: 1 },
              ticks: { stroke: "#c3ced5" },
              size: 60,
            },
      ],
      cursor: { drag: { x: true, y: false } },
      legend: { show: false },
    };
  });

  /**
   * Estimates a vertical gap that keeps stacked traces from overlapping.
   *
   * @param columns - Visible channel columns.
   * @returns Baseline spacing in data units, never zero.
   */
  function stackSpacing(columns: readonly number[][]): number {
    let total = 0;
    let counted = 0;

    for (const column of columns) {
      let min = Infinity;
      let max = -Infinity;
      // Subsampled: an exact peak-to-peak is not needed to pick a gap.
      for (let i = Math.max(0, column.length - 600); i < column.length; i += 4) {
        const value = column[i];
        if (!Number.isFinite(value)) continue;
        if (value < min) min = value;
        if (value > max) max = value;
      }
      if (min === Infinity) continue;
      total += max - min;
      counted += 1;
    }

    if (counted === 0) return 1;
    return (total / counted) * 1.15 || 1;
  }

  /**
   * Labels an x-axis tick as seconds relative to the newest sample.
   *
   * LSL timestamps use the sender's clock, so absolute values are not
   * meaningful to a viewer; elapsed time is.
   *
   * @param value - Tick value in stream timestamp units.
   * @param increment - Spacing between ticks, used to pick precision.
   * @returns Formatted tick label such as `-2.5s`.
   */
  function formatElapsed(value: number, increment: number): string {
    const newest = stream.timestamps[stream.timestamps.length - 1] ?? value;
    const digits = increment < 1 ? 1 : 0;
    return `${(value - newest).toFixed(digits)}s`;
  }

  /**
   * Formats a channel reading for the readings grid.
   *
   * @param value - Latest value for the channel.
   * @param unit - Channel unit, or `unknown` when unreported.
   * @returns Display string with the unit appended when known.
   */
  function formatValue(
    value: number | string | undefined,
    unit: string,
  ): string {
    if (typeof value !== "number") return value ?? "--";
    if (!Number.isFinite(value)) return "--";
    const formatted =
      Math.abs(value) >= 100 ? value.toFixed(1) : value.toFixed(2);
    return unit && unit !== "unknown" ? `${formatted} ${unit}` : formatted;
  }
</script>

<Card.Root class={compact ? "min-w-0 gap-4 py-4" : "min-w-0"}>
  <Card.Header class={compact ? "px-4" : undefined}>
    <div class="flex min-w-0 items-start justify-between gap-4">
      <div class="flex min-w-0 items-center gap-3">
        <div class="stream-icon" class:eeg={stream.isEeg}>
          {#if stream.isEeg}
            <ActivityIcon />
          {:else if stream.type.toLowerCase().includes("gaze")}
            <EyeIcon />
          {:else if stream.type.toLowerCase().includes("physio")}
            <HeartPulseIcon />
          {:else if stream.isMarker}
            <Volume2Icon />
          {:else}
            <RadioIcon />
          {/if}
        </div>
        <div class="min-w-0">
          <Card.Title class="truncate">{stream.name}</Card.Title>
          <Card.Description class="truncate">
            {stream.type} · {stream.labels.length}
            {stream.labels.length === 1 ? "channel" : "channels"}
            {#if effectiveRate > 0}· {effectiveRate.toFixed(0)} Hz{/if}
          </Card.Description>
        </div>
      </div>
      <div class="flex shrink-0 items-center gap-2">
        {#if !stream.isMarker && stream.labels.length > 4 && onToggleStacked}
          <Button
            variant={stacked ? "secondary" : "ghost"}
            size="icon-xs"
            aria-pressed={stacked}
            aria-label="Toggle stacked channel view"
            title="Toggle stacked channel view"
            onclick={onToggleStacked}
          >
            <LayersIcon />
          </Button>
        {/if}
        <span class="live-pill"><span class="dot"></span> Live</span>
      </div>
    </div>
  </Card.Header>

  <Card.Content class={compact ? "px-4" : undefined}>
    {#if stream.isMarker}
      <div class="marker-list" style={`min-height:${compact ? 200 : 300}px`}>
        {#each markerFeed as marker (marker.timestamp)}
          <div class="marker-row">
            <span class="marker-dot"></span>
            <strong class="truncate">{marker.value}</strong>
            <time>{marker.timestamp.toFixed(2)}s</time>
          </div>
        {:else}
          <div class="empty-state">Waiting for marker events…</div>
        {/each}
      </div>
    {:else}
      <div class="chart-shell" style={`min-height:${chartHeight}px`}>
        {#if visibleIndices.length === 0}
          <div class="empty-state">Select a channel to begin plotting.</div>
        {:else if !hasSamples}
          <div class="empty-state">Waiting for samples…</div>
        {:else}
          <UplotChart data={chartData} options={chartOptions} />
        {/if}
      </div>

      {#if !compact}
        <div class="reading-grid">
          {#each stream.labels as label, index (label + index)}
            <div class="reading" class:muted={!selected[index]}>
              <span class="truncate">{label}</span>
              <strong class="truncate">
                {formatValue(latest[index], stream.units[index])}
              </strong>
            </div>
          {/each}
        </div>
      {/if}

      <div class="channel-toolbar">
        <div>
          <strong>Channels</strong>
          <span>{visibleIndices.length} of {stream.labels.length} visible</span>
        </div>
        <div class="flex gap-1">
          <Button
            variant="ghost"
            size="icon-xs"
            aria-label={`Show all ${stream.name} channels`}
            title="Show all channels"
            onclick={() => onSetAll(true)}
          >
            <CheckCheckIcon />
          </Button>
          <Button
            variant="ghost"
            size="icon-xs"
            aria-label={`Hide all ${stream.name} channels`}
            title="Hide all channels"
            onclick={() => onSetAll(false)}
          >
            <SquareXIcon />
          </Button>
        </div>
      </div>

      <div class="channel-grid" class:compact>
        {#each stream.labels as label, index (label + index)}
          <label class:active={selected[index]}>
            <input
              type="checkbox"
              checked={selected[index] ?? false}
              onchange={() => onToggle(index)}
            />
            <span
              class="swatch"
              style={`--channel-color:${CHANNEL_COLORS[index % CHANNEL_COLORS.length]}`}
            ></span>
            <span class="truncate">{label}</span>
            {#if stream.units[index] && stream.units[index] !== "unknown"}
              <small>{stream.units[index]}</small>
            {/if}
          </label>
        {/each}
      </div>
    {/if}
  </Card.Content>
</Card.Root>

<style>
  .stream-icon {
    display: grid;
    width: 2.4rem;
    height: 2.4rem;
    flex: 0 0 auto;
    place-items: center;
    border: 1px solid color-mix(in oklab, var(--primary) 25%, transparent);
    border-radius: 8px;
    background: color-mix(in oklab, var(--primary) 10%, var(--card));
    color: var(--primary);
  }

  .stream-icon :global(svg) {
    width: 1.1rem;
    height: 1.1rem;
  }

  .stream-icon.eeg {
    border-color: color-mix(
      in oklab,
      var(--secondary-foreground) 30%,
      transparent
    );
    background: color-mix(in oklab, var(--secondary) 60%, var(--card));
    color: var(--secondary-foreground);
  }

  .live-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    color: color-mix(in oklab, var(--chart-3) 80%, black);
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
  }

  .live-pill .dot {
    width: 0.45rem;
    height: 0.45rem;
    border-radius: 50%;
    background: var(--chart-3);
    box-shadow: 0 0 0 4px color-mix(in oklab, var(--chart-3) 18%, transparent);
  }

  .chart-shell {
    overflow: hidden;
    border: 1px solid var(--border);
    border-radius: 10px;
    background: color-mix(in oklab, var(--muted) 45%, var(--card));
  }

  .empty-state {
    display: grid;
    min-height: inherit;
    place-items: center;
    padding: 2rem 1rem;
    color: var(--muted-foreground);
    font-size: 0.85rem;
  }

  .reading-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(132px, 1fr));
    gap: 1px;
    margin-top: 1rem;
    overflow: hidden;
    border: 1px solid var(--border);
    border-radius: 10px;
    background: var(--border);
  }

  .reading {
    display: grid;
    gap: 0.15rem;
    min-width: 0;
    padding: 0.65rem 0.8rem;
    background: var(--card);
  }

  .reading span {
    color: var(--muted-foreground);
    font-size: 0.7rem;
  }

  .reading strong {
    color: var(--foreground);
    font-size: 0.9rem;
    font-variant-numeric: tabular-nums;
  }

  .reading.muted {
    opacity: 0.45;
  }

  .channel-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-top: 1rem;
    padding-top: 0.85rem;
    border-top: 1px solid var(--border);
  }

  .channel-toolbar > div:first-child {
    display: grid;
    gap: 0.1rem;
  }

  .channel-toolbar strong {
    color: var(--foreground);
    font-size: 0.78rem;
  }

  .channel-toolbar span {
    color: var(--muted-foreground);
    font-size: 0.7rem;
  }

  .channel-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(146px, 1fr));
    gap: 0.3rem;
    max-height: 14rem;
    margin-top: 0.6rem;
    overflow-y: auto;
  }

  .channel-grid.compact {
    max-height: 7.5rem;
  }

  .channel-grid label {
    display: grid;
    grid-template-columns: auto auto minmax(0, 1fr) auto;
    align-items: center;
    gap: 0.42rem;
    min-width: 0;
    padding: 0.4rem 0.5rem;
    border: 1px solid transparent;
    border-radius: 7px;
    color: var(--muted-foreground);
    cursor: pointer;
    font-size: 0.75rem;
  }

  .channel-grid label:hover {
    background: color-mix(in oklab, var(--accent) 45%, transparent);
  }

  .channel-grid label.active {
    border-color: var(--border);
    background: color-mix(in oklab, var(--muted) 55%, transparent);
    color: var(--foreground);
  }

  .channel-grid input {
    width: 0.85rem;
    height: 0.85rem;
    accent-color: var(--primary);
  }

  .channel-grid small {
    color: var(--muted-foreground);
    font-size: 0.65rem;
  }

  .swatch {
    width: 0.5rem;
    height: 0.5rem;
    border-radius: 2px;
    background: var(--channel-color);
    opacity: 0.3;
  }

  label.active .swatch {
    opacity: 1;
  }

  .marker-list {
    display: grid;
    align-content: start;
    overflow: hidden;
    border: 1px solid var(--border);
    border-radius: 10px;
  }

  .marker-row {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr) auto;
    align-items: center;
    gap: 0.65rem;
    padding: 0.65rem 0.8rem;
    border-bottom: 1px solid var(--border);
    background: var(--card);
  }

  .marker-row:last-child {
    border-bottom: 0;
  }

  .marker-row strong {
    color: var(--foreground);
    font-size: 0.78rem;
  }

  .marker-row time {
    color: var(--muted-foreground);
    font-size: 0.68rem;
    font-variant-numeric: tabular-nums;
  }

  .marker-dot {
    width: 0.45rem;
    height: 0.45rem;
    border-radius: 50%;
    background: var(--chart-5);
  }

  @media (max-width: 640px) {
    .channel-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }
</style>