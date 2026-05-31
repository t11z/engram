<script lang="ts">
  import "../app.css";

  import { token } from "$lib/auth";
  import ConnectScreen from "$lib/components/ConnectScreen.svelte";
  import TopNav from "$lib/components/TopNav.svelte";

  let { children } = $props();
</script>

{#if $token}
  <div class="flex min-h-screen flex-col bg-ink-850">
    <TopNav />
    <main class="mx-auto w-full max-w-6xl flex-1 p-4">
      {@render children()}
    </main>
  </div>
{:else}
  <ConnectScreen />
{/if}
