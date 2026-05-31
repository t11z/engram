<script lang="ts">
  import { connect } from "$lib/auth";

  let value = $state("");

  function submit(event: Event): void {
    event.preventDefault();
    if (value.trim()) connect(value);
  }
</script>

<main class="mx-auto max-w-sm p-8">
  <h1 class="mb-2 font-serif text-2xl">Engram</h1>
  <p class="mb-4 text-sm text-gray-600">
    Enter your server's bearer token to connect to this vault.
  </p>
  <form onsubmit={submit} class="space-y-3">
    <input
      bind:value
      type="password"
      placeholder="ENGRAM_AUTH_TOKEN"
      class="w-full rounded border p-2"
      autocomplete="off"
    />
    <button type="submit" class="w-full rounded bg-black p-2 text-white">Connect</button>
  </form>
</main>
