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

## Static Build

```sh
npm run build
```

After building, run `uv run mobi-view` from the repository root and open
`http://localhost:8765` to view the static frontend served by Python.
