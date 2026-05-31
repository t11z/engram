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
  <p class="font-sans text-sm text-oxide">{error}</p>
{:else if note}
  <article class="rounded-stamp border border-ink-600 bg-ink-850 p-6">
    <!-- Header row -->
    <div class="mb-4 flex items-start justify-between gap-4">
      <h1 class="font-display text-xl font-semibold leading-tight tracking-tight text-chalk-100">{note.title}</h1>
      <button
        type="button"
        class="shrink-0 rounded border border-oxide/40 px-2.5 py-1 font-sans text-xs text-oxide transition-colors duration-150 hover:bg-oxide/10"
        onclick={() => (confirming = true)}
      >
        Delete
      </button>
    </div>

    <!-- Meta row -->
    <div class="mb-5 flex flex-wrap items-center gap-2 border-b border-ink-600 pb-4">
      {#if note.tags && note.tags.length}
        {#each note.tags as tag (tag)}
          <span class="rounded border border-ink-600 bg-ink-800 px-2 py-0.5 font-mono text-xs text-chalk-500">#{tag}</span>
        {/each}
      {/if}
      {#if note.source_url}
        <a
          href={note.source_url}
          target="_blank"
          rel="noopener noreferrer"
          class="ml-auto font-mono text-xs text-slate transition-colors duration-150 hover:text-amber-300"
        >
          Source ↗
        </a>
      {/if}
    </div>

    <MarkdownView body={note.body} />
  </article>
{:else}
  <div class="flex h-48 items-center justify-center rounded-stamp border border-ink-600 bg-ink-800/40">
    <p class="font-mono text-xs uppercase tracking-widest text-chalk-700">Loading…</p>
  </div>
{/if}

{#if confirming}
  <ConfirmDialog
    message="Move this note to the trash?"
    confirmLabel="Delete"
    onconfirm={confirmDelete}
    oncancel={() => (confirming = false)}
  />
{/if}
