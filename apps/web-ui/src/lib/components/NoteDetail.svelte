<script lang="ts">
  import {
    ApiError,
    deleteNote,
    getLinks,
    getNoteWithEtag,
    type Note,
    type OutgoingLink,
  } from "$lib/api";
  import { navTo } from "$lib/nav";
  import { notifyMutation } from "$lib/refresh";

  import BacklinksPanel from "./BacklinksPanel.svelte";
  import ConfirmDialog from "./ConfirmDialog.svelte";
  import GraphView from "./GraphView.svelte";
  import MarkdownView from "./MarkdownView.svelte";
  import NoteEditor from "./NoteEditor.svelte";

  let { path }: { path: string } = $props();
  let note = $state<Note | null>(null);
  let etag = $state("");
  let links = $state<OutgoingLink[]>([]);
  let error = $state("");
  let confirming = $state(false);
  let editing = $state(false);

  async function load(p: string): Promise<void> {
    note = null;
    links = [];
    error = "";
    try {
      const res = await getNoteWithEtag(p);
      if (p !== path) return;
      note = res.note;
      etag = res.etag;
    } catch (e) {
      if (!(e instanceof ApiError && e.isAuth)) {
        error = e instanceof Error ? e.message : "Failed to load note.";
      }
      return;
    }
    try {
      const result = await getLinks(p);
      if (p === path) links = result;
    } catch {
      /* links are non-essential; ignore */
    }
  }

  $effect(() => {
    const current = path;
    editing = false;
    void load(current);
  });

  function followWikilink(target: string): void {
    const link = links.find((l) => l.target === target);
    if (link?.resolved_path) navTo({ note: link.resolved_path });
  }

  function onSaved(updated: Note): void {
    note = updated;
    editing = false;
    void load(path);
  }

  async function confirmDelete(): Promise<void> {
    confirming = false;
    try {
      await deleteNote(path);
      notifyMutation();
      navTo({ note: null });
    } catch (e) {
      if (!(e instanceof ApiError && e.isAuth)) {
        error = e instanceof Error ? e.message : "Delete failed.";
      }
    }
  }
</script>

{#if editing && note}
  <NoteEditor
    {path}
    initialTitle={note.title}
    initialBody={note.body}
    initialTags={note.tags ?? []}
    initialEtag={etag}
    onsaved={onSaved}
    oncancel={() => (editing = false)}
  />
{:else if error}
  <p class="font-sans text-sm text-oxide">{error}</p>
{:else if note}
  <div class="space-y-4">
    <article class="rounded-stamp border border-ink-600 bg-ink-850 p-6">
      <!-- Header row -->
      <div class="mb-4 flex items-start justify-between gap-4">
        <h1 class="font-display text-xl font-semibold leading-tight tracking-tight text-chalk-100">{note.title}</h1>
        <div class="flex shrink-0 gap-2">
          <button
            type="button"
            class="rounded border border-ink-600 px-2.5 py-1 font-sans text-xs text-chalk-400 transition-colors duration-150 hover:text-chalk-100"
            onclick={() => (editing = true)}
          >
            Edit
          </button>
          <button
            type="button"
            class="rounded border border-oxide/40 px-2.5 py-1 font-sans text-xs text-oxide transition-colors duration-150 hover:bg-oxide/10"
            onclick={() => (confirming = true)}
          >
            Delete
          </button>
        </div>
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

      <MarkdownView body={note.body} onwikilink={followWikilink} />
    </article>

    <BacklinksPanel {path} />
    <GraphView {path} />
  </div>
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
