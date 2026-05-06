<script lang="ts">
  const websocketUrl = "ws://localhost:8765";
</script>

<svelte:head>
  <title>MoBI-View</title>
  <meta
    name="description"
    content="MoBI-View browser frontend for real-time LSL stream visualization"
  />
</svelte:head>

<main class="shell">
  <section class="status-panel" aria-labelledby="app-title">
    <div>
      <p class="eyebrow">MoBI-View</p>
      <h1 id="app-title">Real-time stream visualization</h1>
    </div>
    <p class="connection">Frontend scaffold ready for {websocketUrl}</p>
  </section>
</main>

<style>
  :global(body) {
    margin: 0;
    font-family:
      Inter,
      ui-sans-serif,
      system-ui,
      -apple-system,
      BlinkMacSystemFont,
      "Segoe UI",
      sans-serif;
    background: #f7f8fa;
    color: #1f2933;
  }

  .shell {
    min-height: 100vh;
    display: grid;
    place-items: center;
    padding: 2rem;
    box-sizing: border-box;
  }

  .status-panel {
    width: min(100%, 52rem);
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1.5rem;
    border: 1px solid #d8dee8;
    border-radius: 8px;
    background: #ffffff;
    padding: 1.5rem;
    box-shadow: 0 12px 36px rgb(15 23 42 / 0.08);
  }

  .eyebrow {
    margin: 0 0 0.35rem;
    font-size: 0.78rem;
    font-weight: 700;
    text-transform: uppercase;
    color: #3b6ea8;
  }

  h1 {
    margin: 0;
    font-size: clamp(1.5rem, 3vw, 2.25rem);
    line-height: 1.1;
  }

  .connection {
    margin: 0;
    font-family:
      ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono",
      monospace;
    font-size: 0.9rem;
    color: #52606d;
    white-space: nowrap;
  }

  @media (max-width: 700px) {
    .status-panel {
      align-items: flex-start;
      flex-direction: column;
    }

    .connection {
      white-space: normal;
    }
  }
</style>
