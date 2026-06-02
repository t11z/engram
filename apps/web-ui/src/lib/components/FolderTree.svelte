<script lang="ts">
  import { listFolders, ApiError } from "$lib/api";
  import { navTo } from "$lib/nav";

  let { selected = null }: { selected?: string | null } = $props();

  let folders = $state<string[]>([]);
  let error = $state("");

  $effect(() => {
    let cancelled = false;
    listFolders()
      .then((result: string[]) => {
        if (!cancelled) folders = result;
      })
      .catch((e: unknown) => {
        if (cancelled) return;
        if (!(e instanceof ApiError && e.isAuth)) {
          error = e instanceof Error ? e.message : "Failed to load folders.";
        }
      });
    return () => {
      cancelled = true;
    };
  });

  function label(path: string): string {
    const segments = path.split("/");
    return segments[segments.length - 1];
  }

  function depthOf(path: string): number {
    let count = 0;
    for (const char of path) {
      if (char === "/") count += 1;
    }
    return count;
  }
</script>

{#if folders.length > 0}
  <div class="overflow-hidden rounded-stamp border border-ink-600 bg-ink-800">
    <div
      class="border-b border-ink-600 px-4 py-2 font-mono text-xs uppercase tracking-widest text-chalk-500"
    >
      Folders
    </div>
    {#if error}
      <div class="px-4 py-1.5 font-sans text-sm text-chalk-500">{error}</div>
    {/if}
    <button
      type="button"
      onclick={() => navTo({ view: null, note: null, folder: null })}
      class="block w-full px-4 py-1.5 text-left font-sans text-sm transition-colors duration-150"
      class:text-amber-400={selected === null}
      class:text-chalk-400={selected !== null}
      class:hover:bg-ink-750={selected !== null}
      class:hover:text-chalk-200={selected !== null}
    >
      All notes
    </button>
    {#each folders as path (path)}
      {@const isSelected = path === selected}
      <button
        type="button"
        onclick={() => navTo({ view: null, note: null, folder: path })}
        class="block w-full px-4 py-1.5 text-left font-sans text-sm transition-colors duration-150"
        class:text-amber-400={isSelected}
        class:text-chalk-400={!isSelected}
        class:hover:bg-ink-750={!isSelected}
        class:hover:text-chalk-200={!isSelected}
        style="padding-left: {0.75 + depthOf(path) * 0.75}rem"
      >
        {label(path)}
      </button>
    {/each}
  </div>
{/if}
