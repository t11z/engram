<script lang="ts">
  import "../app.css";

  import { token } from "$lib/auth";
  import ConnectScreen from "$lib/components/ConnectScreen.svelte";
  import TopNav from "$lib/components/TopNav.svelte";

  let { children } = $props();
</script>

{#if $token}
  <TopNav />
  <main class="mx-auto max-w-6xl p-4">
    {@render children()}
  </main>
{:else}
  <ConnectScreen />
{/if}
