<script lang="ts">
  let {
    message,
    confirmLabel = "Confirm",
    onconfirm,
    oncancel,
  }: {
    message: string;
    confirmLabel?: string;
    onconfirm: () => void;
    oncancel: () => void;
  } = $props();
</script>

<div
  class="fixed inset-0 z-50 flex items-center justify-center p-4"
  style="background: rgba(7,6,4,0.72); backdrop-filter: blur(6px);"
>
  <div class="w-full max-w-sm rounded-stamp border border-ink-600 bg-ink-800 p-5 shadow-[0_24px_60px_rgba(0,0,0,0.65)]">
    <p class="mb-5 font-sans text-sm text-chalk-300">{message}</p>
    <div class="flex justify-end gap-2">
      <button
        type="button"
        class="rounded border border-ink-600 px-3 py-1.5 font-sans text-sm text-chalk-500 transition-colors duration-150 hover:border-ink-500 hover:text-chalk-300"
        onclick={oncancel}
      >
        Cancel
      </button>
      <button
        type="button"
        class="rounded border border-oxide/40 bg-oxide/10 px-3 py-1.5 font-sans text-sm text-oxide transition-colors duration-150 hover:bg-oxide/20"
        onclick={onconfirm}
      >
        {confirmLabel}
      </button>
    </div>
  </div>
</div>
