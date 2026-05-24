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
  class="block w-full border-b p-3 text-left hover:bg-gray-50"
  class:bg-gray-100={selected}
>
  <div class="font-medium">{item.title}</div>
  {#if snippet}
    <div class="text-sm text-gray-600">{snippet}</div>
  {/if}
  <div class="text-xs text-gray-400">
    {item.updated_at}{#if item.tags && item.tags.length} · {item.tags.join(", ")}{/if}
  </div>
</button>
