import { get, writable } from "svelte/store";

const KEY = "engram_token";

function load(): string | null {
  if (typeof localStorage === "undefined") return null;
  return localStorage.getItem(KEY);
}

export const token = writable<string | null>(load());

token.subscribe((value) => {
  if (typeof localStorage === "undefined") return;
  if (value) localStorage.setItem(KEY, value);
  else localStorage.removeItem(KEY);
});

export function connect(value: string): void {
  token.set(value.trim());
}

export function disconnect(): void {
  token.set(null);
}

export function currentToken(): string | null {
  return get(token);
}
