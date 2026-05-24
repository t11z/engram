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

<div class="fixed inset-0 flex items-center justify-center bg-black/30 p-4">
  <div class="w-full max-w-sm rounded bg-white p-4 shadow-lg">
    <p class="mb-4">{message}</p>
    <div class="flex justify-end gap-2">
      <button type="button" class="rounded px-3 py-1" onclick={oncancel}>Cancel</button>
      <button type="button" class="rounded bg-red-600 px-3 py-1 text-white" onclick={onconfirm}>
        {confirmLabel}
      </button>
    </div>
  </div>
</div>
