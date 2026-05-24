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

<div class="rounded border">
  {#each items as item (item.id)}
    <div class="flex items-center gap-2 border-b p-3">
      <div class="flex-1">
        <div class="font-medium">{item.title}</div>
        <div class="text-xs text-gray-400">{item.updated_at}</div>
      </div>
      <button type="button" class="rounded border px-2 py-1 text-sm" onclick={() => doRestore(item.id)}>
        Restore
      </button>
    </div>
  {/each}
  {#if items.length === 0 && !loading}
    <p class="p-3 text-sm text-gray-500">Trash is empty.</p>
  {/if}
  {#if error}
    <p class="p-3 text-sm text-red-600">{error}</p>
  {/if}
  {#if cursor}
    <button type="button" class="w-full p-2 text-sm" onclick={() => load(false)} disabled={loading}>
      {loading ? "Loading…" : "Load more"}
    </button>
  {/if}
</div>
