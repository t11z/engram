<script lang="ts">
  import { page } from "$app/state";

  import NoteDetail from "$lib/components/NoteDetail.svelte";
  import NoteList from "$lib/components/NoteList.svelte";
  import SearchView from "$lib/components/SearchView.svelte";
  import TrashView from "$lib/components/TrashView.svelte";
  import { parse } from "$lib/nav";

  const nav = $derived(parse(page.url));
</script>

<div class="grid gap-6 md:grid-cols-2">
  <section>
    {#if nav.view === "search"}
      <SearchView q={nav.q} tag={nav.tag} selectedId={nav.note} />
    {:else if nav.view === "trash"}
      <TrashView />
    {:else}
      <NoteList tag={nav.tag} selectedId={nav.note} />
    {/if}
  </section>
  <section>
    {#if nav.note}
      <NoteDetail id={nav.note} />
    {:else}
      <p class="text-gray-500">Select a note to read it.</p>
    {/if}
  </section>
</div>
