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
  <!-- Search input -->
  <div class="flex items-center gap-2.5 rounded-md border border-ink-600 bg-ink-1000 px-3 py-2.5 transition-colors focus-within:border-amber-400 focus-within:shadow-[0_0_0_3px_rgba(217,152,63,0.15)]">
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" class="shrink-0 text-chalk-500">
      <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
    </svg>
    <input
      bind:value={query}
      oninput={onInput}
      type="search"
      placeholder="Search vault…"
      class="flex-1 bg-transparent font-sans text-sm text-chalk-100 outline-none placeholder:text-chalk-700 [&::-webkit-search-cancel-button]:hidden"
    />
    {#if loading}
      <span class="font-mono text-xs text-chalk-700">…</span>
    {/if}
  </div>

  {#if error}
    <p class="font-sans text-sm text-oxide">{error}</p>
  {/if}

  <div class="overflow-hidden rounded-stamp border border-ink-600 bg-ink-800">
    {#each results as item (item.id)}
      <NoteListItem {item} snippet={item.snippet} selected={item.id === selectedId} />
    {/each}
    {#if results.length === 0 && !loading && query.trim()}
      <p class="px-4 py-6 font-mono text-xs uppercase tracking-widest text-chalk-700">No matches.</p>
    {/if}
    {#if !query.trim()}
      <p class="px-4 py-6 font-mono text-xs uppercase tracking-widest text-chalk-700">Ask the vault…</p>
    {/if}
  </div>
</div>
