<script lang="ts">
  import { getGraph, ApiError, type GraphView } from "$lib/api";
  import { navTo } from "$lib/nav";

  let { path }: { path: string } = $props();

  let graph = $state<GraphView | null>(null);
  let error = $state("");

  $effect(() => {
    const current = path;
    error = "";
    graph = null;
    void (async () => {
      try {
        const res = await getGraph(current, 1);
        if (current === path) {
          graph = res;
        }
      } catch (e) {
        if (current === path && !(e instanceof ApiError && e.isAuth)) {
          error = e instanceof Error ? e.message : "Failed to load graph.";
        }
      }
    })();
  });

  const SIZE = 320;
  const CENTER = SIZE / 2;
  const RADIUS = 120;

  const positions = $derived.by<Record<string, { x: number; y: number }>>(() => {
    const map: Record<string, { x: number; y: number }> = {};
    const g = graph;
    if (!g) return map;
    map[g.focus] = { x: CENTER, y: CENTER };
    const others = (g.nodes ?? []).filter((n) => n.path !== g.focus);
    const count = others.length;
    others.forEach((node, i) => {
      const angle = (2 * Math.PI * i) / count;
      map[node.path] = {
        x: CENTER + RADIUS * Math.cos(angle),
        y: CENTER + RADIUS * Math.sin(angle),
      };
    });
    return map;
  });

  function truncate(title: string): string {
    return title.length > 14 ? `${title.slice(0, 13)}…` : title;
  }
</script>

<div class="overflow-hidden rounded-stamp border border-ink-600 bg-ink-800">
  <div
    class="border-b border-ink-600 px-4 py-2 font-mono text-xs uppercase tracking-widest text-chalk-500"
  >
    Local graph
  </div>
  {#if error}
    <p class="px-4 py-3 font-sans text-sm text-oxide">{error}</p>
  {:else if graph && (graph.edges?.length ?? 0) === 0}
    <p class="px-4 py-3 font-mono text-xs uppercase tracking-widest text-chalk-700">No links yet.</p>
  {:else if graph}
    <div class="p-3">
      <svg viewBox="0 0 {SIZE} {SIZE}" class="w-full">
        {#each graph.edges ?? [] as edge (`${edge.source}->${edge.target}:${edge.type}`)}
          {@const a = positions[edge.source]}
          {@const b = positions[edge.target]}
          {#if a && b}
            <line x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke="#463B2D" stroke-width="1" />
          {/if}
        {/each}
        {#each graph.nodes ?? [] as node (node.path)}
          {@const pos = positions[node.path]}
          {#if pos}
            {@const isFocus = node.path === graph.focus}
            <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
            <g
              class={isFocus ? "" : "cursor-pointer"}
              onclick={isFocus ? undefined : () => navTo({ note: node.path })}
            >
              <circle
                cx={pos.x}
                cy={pos.y}
                r={isFocus ? 9 : 6}
                fill={isFocus ? "#D9983F" : "#7C93A6"}
              />
              <text
                x={pos.x}
                y={pos.y + (isFocus ? 22 : 18)}
                fill="#B8AE9C"
                font-size="9"
                text-anchor="middle">{truncate(node.title)}</text
              >
            </g>
          {/if}
        {/each}
      </svg>
    </div>
  {/if}
</div>
