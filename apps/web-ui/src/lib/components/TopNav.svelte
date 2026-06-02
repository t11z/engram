<script lang="ts">
  import { base } from "$app/paths";
  import { page } from "$app/state";

  import { disconnect } from "$lib/auth";
  import { DEMO } from "$lib/demo";
  import { navTo, parse } from "$lib/nav";

  const nav = $derived(parse(page.url));
</script>

<header class="border-b border-ink-600 bg-ink-900">
  <nav class="mx-auto flex max-w-6xl items-center gap-1 px-4 py-3">
    <!-- Logo lockup -->
    <a
      href={base || "/"}
      class="mr-4 flex items-center gap-2.5"
      onclick={(e) => { e.preventDefault(); navTo({ view: null, note: null, q: null, tag: null }); }}
    >
      <img src="{base}/engram-logomark.svg" alt="" class="h-7 w-7" />
      <img src="{base}/engram-wordmark-trans.png" alt="engram" class="h-4 w-auto opacity-90" />
    </a>

    <!-- Nav items -->
    <button
      class="rounded px-3 py-1.5 font-mono text-xs uppercase tracking-widest transition-colors duration-150"
      class:text-amber-400={nav.view === "list" || nav.view === null}
      class:text-chalk-500={nav.view !== "list" && nav.view !== null}
      class:hover:text-chalk-300={nav.view !== "list" && nav.view !== null}
      onclick={() => navTo({ view: null, note: null, q: null, tag: null })}
    >
      Vault
    </button>
    <button
      class="rounded px-3 py-1.5 font-mono text-xs uppercase tracking-widest transition-colors duration-150"
      class:text-amber-400={nav.view === "search"}
      class:text-chalk-500={nav.view !== "search"}
      class:hover:text-chalk-300={nav.view !== "search"}
      onclick={() => navTo({ view: "search", note: null })}
    >
      Search
    </button>
    <button
      class="rounded px-3 py-1.5 font-mono text-xs uppercase tracking-widest transition-colors duration-150"
      class:text-amber-400={nav.view === "trash"}
      class:text-chalk-500={nav.view !== "trash"}
      class:hover:text-chalk-300={nav.view !== "trash"}
      onclick={() => navTo({ view: "trash", note: null })}
    >
      Trash
    </button>
    <button
      class="rounded px-3 py-1.5 font-mono text-xs uppercase tracking-widest transition-colors duration-150"
      class:text-amber-400={nav.compose}
      class:text-chalk-500={!nav.compose}
      class:hover:text-chalk-300={!nav.compose}
      onclick={() => navTo({ view: null, note: null, new: "1" })}
    >
      New
    </button>

    {#if DEMO}
      <span
        class="ml-auto rounded border border-amber-400/40 bg-amber-900/20 px-2.5 py-1 font-mono text-xs uppercase tracking-widest text-amber-400"
        title="Sample data, served entirely in your browser. Changes reset on reload."
      >
        Demo · mock data
      </span>
    {:else}
      <button
        class="ml-auto font-mono text-xs uppercase tracking-widest text-chalk-700 transition-colors duration-150 hover:text-oxide"
        onclick={() => disconnect()}
      >
        Disconnect
      </button>
    {/if}
  </nav>
</header>
