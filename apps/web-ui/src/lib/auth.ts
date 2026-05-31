import { get, writable } from "svelte/store";

import { DEMO, DEMO_TOKEN } from "./demo";

const KEY = "engram_token";

function load(): string | null {
  // In the static demo there is no server to authenticate against; seed a
  // sentinel token so the app renders past the connect screen.
  if (DEMO) return DEMO_TOKEN;
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
