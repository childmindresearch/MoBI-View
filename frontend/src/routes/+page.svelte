<script lang="ts">
  import { ScrollArea } from "$lib/components/ui/scroll-area/index.js";
  import * as Tabs from "$lib/components/ui/tabs/index.js";

  const channels = Array.from(
    { length: 10 },
    (_, index) => `Channel ${index + 1}`,
  );
</script>

<svelte:head>
  <title>MoBI-View</title>
  <meta
    name="description"
    content="MoBI-View browser frontend for real-time LSL stream visualization"
  />
</svelte:head>

<main class="min-h-screen bg-background p-6 text-foreground">
  <Tabs.Root value="channels" class="w-full max-w-md">
    <Tabs.List aria-label="MoBI-View demo tabs">
      <Tabs.Trigger value="channels">Channels</Tabs.Trigger>
      <Tabs.Trigger value="details">Details</Tabs.Trigger>
    </Tabs.List>

    <Tabs.Content value="channels" class="mt-4">
      <ScrollArea class="h-64 rounded-md border">
        <div class="p-4">
          {#each channels as channel}
            <div class="py-2 text-sm">{channel}</div>
          {/each}
        </div>
      </ScrollArea>
    </Tabs.Content>

    <Tabs.Content value="details" class="mt-4 rounded-md border p-4 text-sm">
      Select a channel to view stream details.
    </Tabs.Content>
  </Tabs.Root>
</main>
