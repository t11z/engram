<script lang="ts">
  import { page } from "$app/state";

  import { disconnect } from "$lib/auth";
  import { navTo, parse } from "$lib/nav";

  const nav = $derived(parse(page.url));
</script>

<header class="border-b">
  <nav class="mx-auto flex max-w-6xl items-center gap-4 p-4">
    <span class="font-serif text-lg">Engram</span>
    <button class:font-semibold={nav.view === "list"} onclick={() => navTo({ view: null, note: null, q: null, tag: null })}>
      Notes
    </button>
    <button class:font-semibold={nav.view === "search"} onclick={() => navTo({ view: "search", note: null })}>
      Search
    </button>
    <button class:font-semibold={nav.view === "trash"} onclick={() => navTo({ view: "trash", note: null })}>
      Trash
    </button>
    <button class="ml-auto text-sm text-gray-600" onclick={() => disconnect()}>Disconnect</button>
  </nav>
</header>
