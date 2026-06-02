<script lang="ts">
  import { onMount } from "svelte";
  import { listTags, ApiError, type TagCount } from "$lib/api";
  import { navTo } from "$lib/nav";

  let { selected = null }: { selected?: string | null } = $props();

  let tags = $state<TagCount[]>([]);

  onMount(async () => {
    try {
      tags = await listTags();
    } catch (e) {
      // A failed tag list just leaves the browser empty; auth errors are handled
      // globally by the API client. Don't surface noise in the sidebar.
      if (e instanceof ApiError && e.isAuth) return;
    }
  });

  function toggle(tag: string): void {
    navTo({ view: null, note: null, tag: tag === selected ? null : tag });
  }
</script>

{#if tags.length}
  <div class="overflow-hidden rounded-stamp border border-ink-600 bg-ink-800">
    <div
      class="border-b border-ink-600 px-4 py-2 font-mono text-xs uppercase tracking-widest text-chalk-500"
    >
      Tags
    </div>
    <div class="flex flex-wrap gap-1.5 p-3">
      {#each tags as { tag, count } (tag)}
        <button
          type="button"
          onclick={() => toggle(tag)}
          class="rounded bg-ink-700 px-2 py-0.5 font-mono text-xs transition-colors duration-150"
          class:text-amber-400={tag === selected}
          class:text-chalk-400={tag !== selected}
          class:hover:text-chalk-200={tag !== selected}
        >
          #{tag} <span class="text-chalk-700">{count}</span>
        </button>
      {/each}
    </div>
  </div>
{/if}
