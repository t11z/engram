<script lang="ts">
  import { base } from "$app/paths";

  import { connect } from "$lib/auth";

  let value = $state("");

  function submit(event: Event): void {
    event.preventDefault();
    if (value.trim()) connect(value);
  }
</script>

<div class="flex min-h-screen items-center justify-center bg-ink-900 p-8"
  style="background-image: radial-gradient(800px 400px at 50% 0%, rgba(217,152,63,0.06), transparent 60%);">
  <div class="w-full max-w-sm">
    <!-- Logo -->
    <div class="mb-8 flex flex-col items-center gap-4">
      <img src="{base}/engram-logomark.svg" alt="" class="h-14 w-14" style="filter: drop-shadow(0 0 18px rgba(217,152,63,0.22));" />
      <img src="{base}/engram-wordmark-trans.png" alt="engram" class="h-5 w-auto opacity-80" />
    </div>

    <!-- Card -->
    <div class="rounded-stamp border border-ink-600 bg-ink-800 p-6 shadow-[0_8px_32px_rgba(0,0,0,0.5)]">
      <p class="mb-1 font-mono text-xs uppercase tracking-widest text-amber-400">Engram Vault</p>
      <p class="mb-5 text-sm text-chalk-500">
        Enter your server's bearer token to connect.
      </p>
      <form onsubmit={submit} class="space-y-3">
        <div class="flex items-center gap-2.5 rounded-md border border-ink-600 bg-ink-1000 px-3 py-2.5 transition-colors focus-within:border-amber-400 focus-within:shadow-[0_0_0_3px_rgba(217,152,63,0.15)]">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" class="shrink-0 text-chalk-700">
            <circle cx="7.5" cy="15.5" r="5.5"/><path d="M21 2l-9.6 9.6"/><path d="M15.5 7.5l3 3L22 7l-3-3"/>
          </svg>
          <input
            bind:value
            type="password"
            placeholder="ENGRAM_AUTH_TOKEN"
            class="flex-1 bg-transparent font-mono text-sm text-chalk-100 outline-none placeholder:text-chalk-700"
            autocomplete="off"
          />
        </div>
        <button
          type="submit"
          class="w-full rounded-md bg-amber-400 px-4 py-2.5 font-sans text-sm font-semibold text-ink-1000 transition-colors duration-150 hover:bg-amber-300 active:bg-amber-500"
        >
          Connect to vault
        </button>
      </form>
    </div>

    <p class="mt-4 text-center font-mono text-xs text-chalk-700">
      Self-hosted · No account · Your data
    </p>
  </div>
</div>
