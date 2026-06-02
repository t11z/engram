<script lang="ts">
  import { page } from "$app/state";

  import FolderTree from "$lib/components/FolderTree.svelte";
  import NoteDetail from "$lib/components/NoteDetail.svelte";
  import NoteEditor from "$lib/components/NoteEditor.svelte";
  import NoteList from "$lib/components/NoteList.svelte";
  import SearchView from "$lib/components/SearchView.svelte";
  import TagBrowser from "$lib/components/TagBrowser.svelte";
  import TrashView from "$lib/components/TrashView.svelte";
  import { navTo, parse } from "$lib/nav";

  const nav = $derived(parse(page.url));
</script>

<div class="grid gap-4 md:grid-cols-[320px_1fr]">
  <section class="min-h-0">
    {#if nav.view === "search"}
      <SearchView q={nav.q} tag={nav.tag} selectedPath={nav.note} />
    {:else if nav.view === "trash"}
      <TrashView />
    {:else}
      <div class="space-y-3">
        <TagBrowser selected={nav.tag} />
        <FolderTree selected={nav.folder} />
        <NoteList tag={nav.tag} folder={nav.folder} selectedPath={nav.note} />
      </div>
    {/if}
  </section>
  <section class="min-h-0">
    {#if nav.compose}
      <NoteEditor
        onsaved={(note) => navTo({ new: null, note: note.path })}
        oncancel={() => navTo({ new: null })}
      />
    {:else if nav.note}
      <NoteDetail path={nav.note} />
    {:else}
      <div class="flex h-48 items-center justify-center rounded-stamp border border-ink-600 bg-ink-800/40">
        <p class="font-mono text-xs uppercase tracking-widest text-chalk-700">Select a note to read it</p>
      </div>
    {/if}
  </section>
</div>
