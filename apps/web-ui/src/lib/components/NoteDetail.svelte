<script lang="ts">
  import { ApiError, deleteNote, getNote, type Note } from "$lib/api";
  import { navTo } from "$lib/nav";
  import { notifyMutation } from "$lib/refresh";

  import ConfirmDialog from "./ConfirmDialog.svelte";
  import MarkdownView from "./MarkdownView.svelte";

  let { id }: { id: string } = $props();
  let note = $state<Note | null>(null);
  let error = $state("");
  let confirming = $state(false);

  $effect(() => {
    const current = id;
    note = null;
    error = "";
    void getNote(current)
      .then((n) => {
        if (current === id) note = n;
      })
      .catch((e) => {
        if (!(e instanceof ApiError && e.isAuth)) {
          error = e instanceof Error ? e.message : "Failed to load note.";
        }
      });
  });

  async function confirmDelete(): Promise<void> {
    confirming = false;
    try {
      await deleteNote(id);
      notifyMutation();
      navTo({ note: null });
    } catch (e) {
      if (!(e instanceof ApiError && e.isAuth)) {
        error = e instanceof Error ? e.message : "Delete failed.";
      }
    }
  }
</script>

{#if error}
  <p class="text-red-600">{error}</p>
{:else if note}
  <article class="space-y-3">
    <div class="flex items-start justify-between gap-4">
      <h1 class="text-xl font-semibold">{note.title}</h1>
      <button
        type="button"
        class="shrink-0 rounded border border-red-600 px-2 py-1 text-sm text-red-600"
        onclick={() => (confirming = true)}
      >
        Delete
      </button>
    </div>
    {#if note.tags && note.tags.length}
      <div class="text-sm text-gray-500">{note.tags.join(", ")}</div>
    {/if}
    {#if note.source_url}
      <a href={note.source_url} target="_blank" rel="noopener noreferrer" class="text-sm text-blue-600 underline">
        Source
      </a>
    {/if}
    <MarkdownView body={note.body} />
  </article>
{:else}
  <p class="text-gray-500">Loading…</p>
{/if}

{#if confirming}
  <ConfirmDialog
    message="Move this note to the trash?"
    confirmLabel="Delete"
    onconfirm={confirmDelete}
    oncancel={() => (confirming = false)}
  />
{/if}
