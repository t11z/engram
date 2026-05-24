import { writable } from "svelte/store";

/** Bumped after a mutation (delete/restore) so list views reload. */
export const mutations = writable(0);

export function notifyMutation(): void {
  mutations.update((n) => n + 1);
}
