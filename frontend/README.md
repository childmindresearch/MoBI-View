# MoBI-View Frontend

SvelteKit frontend for the MoBI-View browser UI.

The app is built as static HTML, JavaScript, and CSS with `@sveltejs/adapter-static`.
Production assets are emitted directly to `../src/MoBI_View/web/static`, which is
the directory served by the Python WebSocket/HTTP server.

UI styling is initialized with Tailwind CSS v4 and shadcn-svelte. No shadcn
components are checked in yet; add them only when a feature needs them.

## Commands

```sh
npm run dev
npm run check
npm run format:check
npm run build
```

## Backend Contract

During local development, the frontend expects the Python server to be available at
`ws://localhost:8765`.

The current backend message contract is:

- Send discovery command: `{"command":"discover"}`
- Receive discovery response: `{"type":"discover_result","streams":[...]}`
- Receive broadcast frame: `{"streams":[{"stream_name":"...","samples":[[1,2]],"timestamps":[10],"channel_labels":["a","b"]}]}`

Each `samples` row contains numeric channel values or marker strings, with one
timestamp per row. `stream_type` and `channel_units` are optional. Invalid stream
entries are dropped with a warning without discarding valid entries in the frame.

## Stream Stores

`src/lib/stores/streams.ts` exposes stores fed by the WebSocket connection:

Incoming data updates internal state and `streamHistory` immediately.
`revision`, `streamSamples`, and `orderedStreams` publish together at most once
per `requestAnimationFrame`; without `requestAnimationFrame` they publish
synchronously. `discoveredStreams` publishes immediately.

- `revision`: a number that increments on every publication, including after
  `clearHistory()`; read `streamHistory` when it changes.
- `streamSamples`: the most recent raw batch per stream, including empty
  batches, as of the last publication.
- `streamHistory`: a plain, non-reactive `ReadonlyMap` keyed by stream name
  holding a bounded rolling window per stream; the map keeps its identity:
  - `category`: `eeg`, `numeric`, or `marker` (see Classification below).
  - `timestamps`: retained row timestamps, oldest first (numeric streams only).
  - `values`: one numeric array per channel, aligned with `timestamps`;
    non-finite numbers are stored as `NaN`. Empty for marker streams.
  - `markers`: `{ timestamp, value, channelIndex }` events for marker streams,
    one per channel per row in row-then-channel order. `value` keeps the
    received number or string; `channelIndex` is the zero-based originating
    channel, labelled by `channel_labels[channelIndex]`. Empty for numeric
    streams.
  - `latest`: the raw final row of the most recent non-empty batch; empty
    until data arrives. Empty batches keep it.
  - `sampleCount`: cumulative rows received, unaffected by trimming, resets,
    or clearing.
  - `channel_labels`: the stream's current channel layout.

  Numeric streams keep at most `MAX_POINTS` (1250) newest rows; marker streams
  keep at most `MAX_MARKERS` (250) newest events (not rows), so the oldest
  retained event may start mid-row by design. Overflow is
  trimmed once per batch. If a stream's `channel_labels`, `stream_type`, or
  category change, retained buffers (including markers, so `channelIndex`
  never points at a stale label) and `latest` reset while `sampleCount`
  continues; a stream that becomes a marker keeps no numeric rows and stores
  its whole current batch as events. History objects and arrays are mutated
  in place.

- `orderedStreams`: latest batches in display order, shared by the sidebar and
  Channels tab: EEG first, other numeric next, markers last, ties by stream
  name.
- `clearHistory()`: empties every stream's `timestamps`, `values` (keeping one
  empty column per numeric channel), and `markers`. `latest`, `sampleCount`,
  classification, `streamSamples`, `orderedStreams`, discovery, and the
  connection are untouched; new data appends normally. Consumers are notified
  through the next `revision` publication.
- `discoveredStreams`: names from the latest discovery response; discovery does
  not populate sample or history stores.

`stopStreamStores` (or `stop` from `createStreamStores`) cancels any pending
publication and ends all updates; already received history is kept.

### Seen Streams

Stream lists hold every stream seen in a data frame for the lifetime of the
store instance (the page load for the app-wide stores), not only streams that
are currently sending. A stream is never removed because a frame omits it:
sparse or empty frames, quiet marker streams, and WebSocket reconnects keep
existing entries, which update again when new data arrives. `clearHistory()`
clears buffers, not membership. There is no expiry or removal API.

### Classification

`src/lib/stream-classification.ts` classifies each stream. A case-insensitive
`Markers` `stream_type` or any string sample makes it a marker stream; it stays
one until its channel layout or `stream_type` changes. Otherwise a
case-insensitive `EEG` type is `eeg` and anything else is `numeric`.

## Static Build

```sh
npm run build
```

After building, run `uv run mobi-view` from the repository root and open
`http://localhost:8765` to view the static frontend served by Python.
