<script lang="ts">
  import { renderMarkdown } from "$lib/markdown";

  let { body, onwikilink }: { body: string; onwikilink?: (target: string) => void } = $props();
  let html = $state("");

  $effect(() => {
    const source = body;
    void renderMarkdown(source).then((result) => {
      html = result;
    });
  });

  function handleClick(event: MouseEvent): void {
    if (!onwikilink) return;
    const anchor = (event.target as HTMLElement | null)?.closest("a.wikilink");
    const target = anchor?.getAttribute("data-target");
    if (target) {
      event.preventDefault();
      onwikilink(target);
    }
  }
</script>

<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
<div class="prose max-w-none" onclick={handleClick}>
  <!-- eslint-disable-next-line svelte/no-at-html-tags -- html is sanitized by renderMarkdown -->
  {@html html}
</div>
