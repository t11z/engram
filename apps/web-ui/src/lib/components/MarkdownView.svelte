<script lang="ts">
  import { renderMarkdown } from "$lib/markdown";

  let { body }: { body: string } = $props();
  let html = $state("");

  $effect(() => {
    const source = body;
    void renderMarkdown(source).then((result) => {
      html = result;
    });
  });
</script>

<div class="prose max-w-none">
  <!-- eslint-disable-next-line svelte/no-at-html-tags -- html is sanitized by renderMarkdown -->
  {@html html}
</div>
