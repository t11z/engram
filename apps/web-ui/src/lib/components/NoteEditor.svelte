<script lang="ts">
  import { ApiError, createNote, getNoteWithEtag, updateNote, type Note } from "$lib/api";
  import { notifyMutation } from "$lib/refresh";

  import MarkdownView from "./MarkdownView.svelte";

  let {
    path = null,
    initialTitle = "",
    initialBody = "",
    initialTags = [],
    initialEtag = "",
    onsaved,
    oncancel,
  }: {
    path?: string | null;
    initialTitle?: string;
    initialBody?: string;
    initialTags?: string[];
    initialEtag?: string;
    onsaved: (note: Note) => void;
    oncancel: () => void;
  } = $props();

  let title = $state(initialTitle);
  let body = $state(initialBody);
  let tagsInput = $state(initialTags.join(", "));
  let etag = $state(initialEtag);
  let saving = $state(false);
  let error = $state("");
  let conflict = $state(false);
  let preview = $state(false);

  const inputClass =
    "w-full rounded border border-ink-600 bg-ink-1000 px-3 py-2 font-sans text-sm text-chalk-100 outline-none transition-colors focus:border-amber-400";

  function parseTags(): string[] {
    return tagsInput
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean);
  }

  async function save(): Promise<void> {
    if (!title.trim()) {
      error = "A title is required.";
      return;
    }
    saving = true;
    error = "";
    conflict = false;
    try {
      if (path) {
        const res = await updateNote(path, { title, body, tags: parseTags() }, etag);
        etag = res.etag;
        notifyMutation();
        onsaved(res.note);
      } else {
        const note = await createNote({ title, body, tags: parseTags() });
        notifyMutation();
        onsaved(note);
      }
    } catch (e) {
      if (e instanceof ApiError && e.isAuth) return;
      if (e instanceof ApiError && e.status === 409) conflict = true;
      else error = e instanceof Error ? e.message : "Save failed.";
    } finally {
      saving = false;
    }
  }

  async function reloadLatest(): Promise<void> {
    if (!path) return;
    try {
      const res = await getNoteWithEtag(path);
      title = res.note.title;
      body = res.note.body;
      tagsInput = (res.note.tags ?? []).join(", ");
      etag = res.etag;
      conflict = false;
      error = "";
    } catch (e) {
      if (!(e instanceof ApiError && e.isAuth)) error = "Could not reload the note.";
    }
  }

  async function overwrite(): Promise<void> {
    if (!path) return;
    try {
      const res = await getNoteWithEtag(path);
      etag = res.etag;
      conflict = false;
      await save();
    } catch (e) {
      if (!(e instanceof ApiError && e.isAuth)) error = "Could not resolve the conflict.";
    }
  }
</script>

<div class="space-y-3 rounded-stamp border border-ink-600 bg-ink-850 p-6">
  <div class="flex items-center justify-between gap-3">
    <span class="font-mono text-xs uppercase tracking-widest text-chalk-500">
      {path ? "Edit note" : "New note"}
    </span>
    <div class="flex gap-2">
      <button
        type="button"
        class="rounded border border-ink-600 px-2.5 py-1 font-mono text-xs uppercase tracking-wider text-chalk-500 transition-colors hover:text-chalk-200"
        onclick={() => (preview = !preview)}
      >
        {preview ? "Edit" : "Preview"}
      </button>
      <button
        type="button"
        class="rounded border border-ink-600 px-2.5 py-1 font-mono text-xs uppercase tracking-wider text-chalk-500 transition-colors hover:text-chalk-200"
        onclick={oncancel}
      >
        Cancel
      </button>
      <button
        type="button"
        class="rounded border border-amber-400/50 bg-amber-900/20 px-2.5 py-1 font-mono text-xs uppercase tracking-wider text-amber-400 transition-colors hover:bg-amber-900/30 disabled:opacity-40"
        onclick={save}
        disabled={saving}
      >
        {saving ? "Saving…" : "Save"}
      </button>
    </div>
  </div>

  <input bind:value={title} placeholder="Title" class={inputClass} />
  <input bind:value={tagsInput} placeholder="tags, comma, separated" class={inputClass} />

  {#if preview}
    <div class="min-h-[16rem] rounded border border-ink-600 bg-ink-900 p-4">
      <MarkdownView {body} />
    </div>
  {:else}
    <textarea
      bind:value={body}
      rows="18"
      placeholder="Write in Markdown… [[wikilinks]] and #tags work."
      class="{inputClass} resize-y font-mono leading-relaxed"
    ></textarea>
  {/if}

  {#if conflict}
    <div class="rounded border border-oxide/40 bg-oxide/10 p-3 font-sans text-sm text-chalk-200">
      <p class="mb-2">This note changed on disk since you opened it.</p>
      <div class="flex gap-2">
        <button
          type="button"
          class="rounded border border-ink-600 px-2.5 py-1 font-mono text-xs uppercase tracking-wider text-chalk-300 hover:text-chalk-100"
          onclick={reloadLatest}
        >
          Reload latest (discard my edits)
        </button>
        <button
          type="button"
          class="rounded border border-oxide/50 px-2.5 py-1 font-mono text-xs uppercase tracking-wider text-oxide hover:bg-oxide/10"
          onclick={overwrite}
        >
          Overwrite
        </button>
      </div>
    </div>
  {/if}

  {#if error}
    <p class="font-sans text-sm text-oxide">{error}</p>
  {/if}
</div>
