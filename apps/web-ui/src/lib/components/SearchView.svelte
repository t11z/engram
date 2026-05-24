<script lang="ts">
  import { ApiError, search, type SearchResult } from "$lib/api";

  import NoteListItem from "./NoteListItem.svelte";

  let { q = "", tag = null, selectedId = null }: { q?: string; tag?: string | null; selectedId?: string | null } =
    $props();

  let query = $state("");
  let results = $state<SearchResult[]>([]);
  let loading = $state(false);
  let error = $state("");
  let timer: ReturnType<typeof setTimeout> | undefined;

  async function run(): Promise<void> {
    const term = query.trim();
    if (!term) {
      results = [];
      return;
    }
    loading = true;
    error = "";
    try {
      const res = await search({ q: term, tag });
      results = res.items;
    } catch (e) {
      if (!(e instanceof ApiError && e.isAuth)) {
        error = e instanceof Error ? e.message : "Search failed.";
      }
    } finally {
      loading = false;
    }
  }

  function onInput(): void {
    clearTimeout(timer);
    timer = setTimeout(() => void run(), 250);
  }

  $effect(() => {
    query = q;
    if (q) void run();
  });
</script>

<div class="space-y-3">
  <input
    bind:value={query}
    oninput={onInput}
    type="search"
    placeholder="Search notes…"
    class="w-full rounded border p-2"
  />
  {#if error}
    <p class="text-sm text-red-600">{error}</p>
  {/if}
  <div class="rounded border">
    {#each results as item (item.id)}
      <NoteListItem {item} snippet={item.snippet} selected={item.id === selectedId} />
    {/each}
    {#if results.length === 0 && !loading && query.trim()}
      <p class="p-3 text-sm text-gray-500">No matches.</p>
    {/if}
  </div>
</div>
