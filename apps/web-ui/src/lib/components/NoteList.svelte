<script lang="ts">
  import { untrack } from "svelte";

  import { ApiError, listNotes, type NoteSummary } from "$lib/api";
  import { mutations } from "$lib/refresh";

  import NoteListItem from "./NoteListItem.svelte";

  let { tag = null, selectedId = null }: { tag?: string | null; selectedId?: string | null } = $props();

  let items = $state<NoteSummary[]>([]);
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

<div class="rounded border">
  {#each items as item (item.id)}
    <NoteListItem {item} selected={item.id === selectedId} />
  {/each}
  {#if items.length === 0 && !loading}
    <p class="p-3 text-sm text-gray-500">No notes yet.</p>
  {/if}
  {#if error}
    <p class="p-3 text-sm text-red-600">{error}</p>
  {/if}
  {#if cursor}
    <button
      type="button"
      class="w-full p-2 text-sm text-gray-600 hover:bg-gray-50"
      onclick={() => load(false)}
      disabled={loading}
    >
      {loading ? "Loading…" : "Load more"}
    </button>
  {/if}
</div>
