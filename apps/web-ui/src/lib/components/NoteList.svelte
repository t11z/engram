<script lang="ts">
  import { untrack } from "svelte";

  import { ApiError, listNotes, type NoteSummary } from "$lib/api";
  import { mutations } from "$lib/refresh";

  import NoteListItem from "./NoteListItem.svelte";

  let {
    tag = null,
    folder = null,
    selectedPath = null,
  }: { tag?: string | null; folder?: string | null; selectedPath?: string | null } = $props();

  let items = $state<NoteSummary[]>([]);
  // Folder filtering is applied client-side over loaded pages (the list API
  // filters by tag, not path); selecting a folder narrows what's shown.
  const shown = $derived(
    folder ? items.filter((item) => item.path.startsWith(`${folder}/`)) : items,
  );
  let cursor = $state<string | null>(null);
  let loading = $state(false);
  let error = $state("");

  async function load(reset: boolean): Promise<void> {
    loading = true;
    error = "";
    try {
      const res = await listNotes({ cursor: reset ? undefined : (cursor ?? undefined), tag });
      items = reset ? res.items : [...items, ...res.items];
      cursor = res.next_cursor ?? null;
    } catch (e) {
      if (!(e instanceof ApiError && e.isAuth)) {
        error = e instanceof Error ? e.message : "Failed to load notes.";
      }
    } finally {
      loading = false;
    }
  }

  $effect(() => {
    tag;
    $mutations;
    untrack(() => void load(true));
  });
</script>

<div class="overflow-hidden rounded-stamp border border-ink-600 bg-ink-800">
  {#each shown as item (item.path)}
    <NoteListItem {item} selected={item.path === selectedPath} />
  {/each}
  {#if shown.length === 0 && !loading}
    <p class="px-4 py-6 font-mono text-xs uppercase tracking-widest text-chalk-700">
      Nothing inscribed yet.
    </p>
  {/if}
  {#if error}
    <p class="px-4 py-3 font-sans text-sm text-oxide">{error}</p>
  {/if}
  {#if cursor}
    <button
      type="button"
      class="w-full border-t border-ink-600 px-4 py-2.5 font-mono text-xs uppercase tracking-widest text-chalk-500 transition-colors duration-150 hover:bg-ink-750 hover:text-chalk-300 disabled:opacity-40"
      onclick={() => load(false)}
      disabled={loading}
    >
      {loading ? "Loading…" : "Load more"}
    </button>
  {/if}
</div>
