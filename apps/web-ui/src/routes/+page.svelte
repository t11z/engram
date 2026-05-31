<script lang="ts">
  import { page } from "$app/state";

  import NoteDetail from "$lib/components/NoteDetail.svelte";
  import NoteList from "$lib/components/NoteList.svelte";
  import SearchView from "$lib/components/SearchView.svelte";
  import TrashView from "$lib/components/TrashView.svelte";
  import { parse } from "$lib/nav";

  const nav = $derived(parse(page.url));
</script>

<div class="grid gap-4 md:grid-cols-[320px_1fr]">
  <section class="min-h-0">
    {#if nav.view === "search"}
      <SearchView q={nav.q} tag={nav.tag} selectedId={nav.note} />
    {:else if nav.view === "trash"}
      <TrashView />
    {:else}
      <NoteList tag={nav.tag} selectedId={nav.note} />
    {/if}
  </section>
  <section class="min-h-0">
    {#if nav.note}
      <NoteDetail id={nav.note} />
    {:else}
      <div class="flex h-48 items-center justify-center rounded-stamp border border-ink-600 bg-ink-800/40">
        <p class="font-mono text-xs uppercase tracking-widest text-chalk-700">Select a note to read it</p>
      </div>
    {/if}
  </section>
</div>
