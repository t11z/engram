<script lang="ts">
  import { untrack } from "svelte";

  import { ApiError, listTrash, restore, type NoteSummary } from "$lib/api";
  import { mutations, notifyMutation } from "$lib/refresh";

  // Trashed notes are not viewable (GET /notes/{id} is live-only), so rows are
  // not clickable — only restorable.
  let items = $state<NoteSummary[]>([]);
  let cursor = $state<string | null>(null);
  let loading = $state(false);
  let error = $state("");

  async function load(reset: boolean): Promise<void> {
    loading = true;
    error = "";
    try {
      const res = await listTrash({ cursor: reset ? undefined : (cursor ?? undefined) });
      items = reset ? res.items : [...items, ...res.items];
      cursor = res.next_cursor ?? null;
    } catch (e) {
      if (!(e instanceof ApiError && e.isAuth)) {
        error = e instanceof Error ? e.message : "Failed to load trash.";
      }
    } finally {
      loading = false;
    }
  }

  async function doRestore(id: string): Promise<void> {
    try {
      await restore(id);
      notifyMutation();
    } catch (e) {
      if (!(e instanceof ApiError && e.isAuth)) {
        error = e instanceof Error ? e.message : "Restore failed.";
      }
    }
  }

  $effect(() => {
    $mutations;
    untrack(() => void load(true));
  });
</script>

<div class="overflow-hidden rounded-stamp border border-ink-600 bg-ink-800">
  {#each items as item (item.id)}
    <div class="flex items-center gap-3 border-b border-ink-600 px-4 py-3 last:border-b-0">
      <div class="flex-1 min-w-0">
        <div class="truncate font-sans text-sm font-medium text-chalk-300">{item.title}</div>
        <div class="font-mono text-xs text-chalk-700">{item.updated_at}</div>
      </div>
      <button
        type="button"
        class="shrink-0 rounded border border-ink-600 px-2.5 py-1 font-mono text-xs uppercase tracking-wider text-chalk-500 transition-colors duration-150 hover:border-sage hover:text-sage"
        onclick={() => doRestore(item.id)}
      >
        Restore
      </button>
    </div>
  {/each}
  {#if items.length === 0 && !loading}
    <p class="px-4 py-6 font-mono text-xs uppercase tracking-widest text-chalk-700">Trash is empty.</p>
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
