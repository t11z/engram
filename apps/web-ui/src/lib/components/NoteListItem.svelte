<script lang="ts">
  import type { NoteSummary } from "$lib/api";
  import { navTo } from "$lib/nav";

  let {
    item,
    snippet = "",
    selected = false,
  }: { item: NoteSummary; snippet?: string; selected?: boolean } = $props();
</script>

<button
  type="button"
  onclick={() => navTo({ note: item.id })}
  class="block w-full border-b border-ink-600 px-4 py-3 text-left transition-colors duration-150 last:border-b-0"
  class:bg-amber-900={selected}
  class:bg-opacity-20={selected}
  class:border-l-2={selected}
  class:border-l-amber-400={selected}
  class:pl-3.5={selected}
  class:hover:bg-ink-750={!selected}
>
  <div class="font-sans text-sm font-medium text-chalk-100 leading-snug">{item.title}</div>
  {#if snippet}
    <div class="mt-0.5 font-sans text-xs text-chalk-500 line-clamp-2">{snippet}</div>
  {/if}
  <div class="mt-1.5 flex items-center gap-2">
    <span class="font-mono text-xs text-chalk-700">{item.updated_at}</span>
    {#if item.tags && item.tags.length}
      {#each item.tags.slice(0, 3) as tag}
        <span class="rounded bg-ink-700 px-1.5 py-px font-mono text-xs text-chalk-500">#{tag}</span>
      {/each}
    {/if}
  </div>
</button>
