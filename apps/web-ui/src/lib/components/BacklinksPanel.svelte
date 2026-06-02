<script lang="ts">
  import { getBacklinks, ApiError, type NoteSummary } from "$lib/api";
  import { navTo } from "$lib/nav";

  let { path }: { path: string } = $props();

  let items = $state<NoteSummary[]>([]);
  let error = $state("");

  $effect(() => {
    const current = path;
    error = "";
    void (async () => {
      try {
        const res = await getBacklinks(current);
        if (current === path) {
          items = res.items;
        }
      } catch (e) {
        if (current === path && !(e instanceof ApiError && e.isAuth)) {
          error = e instanceof Error ? e.message : "Failed to load backlinks.";
        }
      }
    })();
  });
</script>

<div class="overflow-hidden rounded-stamp border border-ink-600 bg-ink-800">
  <div
    class="border-b border-ink-600 px-4 py-2 font-mono text-xs uppercase tracking-widest text-chalk-500"
  >
    Backlinks
  </div>
  {#each items as item (item.path)}
    <button
      type="button"
      onclick={() => navTo({ note: item.path })}
      class="block w-full border-b border-ink-600 px-4 py-2.5 text-left transition-colors duration-150 last:border-b-0 hover:bg-ink-750"
    >
      <div class="font-sans text-sm text-chalk-300">{item.title}</div>
      <div class="font-mono text-xs text-chalk-700">{item.updated_at}</div>
    </button>
  {/each}
  {#if items.length === 0 && !error}
    <p class="px-4 py-3 font-mono text-xs uppercase tracking-widest text-chalk-700">
      No backlinks yet.
    </p>
  {/if}
  {#if error}
    <p class="px-4 py-3 font-sans text-sm text-oxide">{error}</p>
  {/if}
</div>
