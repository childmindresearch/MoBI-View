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
  <section
    class="flex w-full max-w-3xl items-center justify-between gap-6 rounded-lg border bg-card p-6 text-card-foreground shadow-sm max-sm:flex-col max-sm:items-start"
    aria-labelledby="app-title"
  >
    <div>
      <p class="mb-1 text-xs font-semibold text-muted-foreground uppercase">
        MoBI-View
      </p>
      <h1 id="app-title" class="text-3xl leading-tight font-semibold">
        Real-time stream visualization
      </h1>
    </div>
    <p class="font-mono text-sm text-muted-foreground max-sm:break-all">
      Frontend scaffold ready for {websocketUrl}
    </p>
  </section>
</main>

<style>
  .shell {
    min-height: 100vh;
    display: grid;
    place-items: center;
    padding: 2rem;
    box-sizing: border-box;
  }
</style>
