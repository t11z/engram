/**
 * Demo mode: built with `VITE_ENGRAM_DEMO=1`, the app talks to an in-memory
 * mock store instead of a live `/api/v1` server. Used for the static demo
 * published on GitHub Pages, where there is no backend.
 */
export const DEMO = import.meta.env.VITE_ENGRAM_DEMO === "1";

/** Sentinel token used to satisfy the auth gate in demo mode. */
export const DEMO_TOKEN = "demo";
