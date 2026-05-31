import process from "node:process";
import { fileURLToPath } from "node:url";

import adapter from "@sveltejs/adapter-static";
import { vitePreprocess } from "@sveltejs/vite-plugin-svelte";

const contract = fileURLToPath(new URL("../../packages/contract/types.ts", import.meta.url));

/** @type {import('@sveltejs/kit').Config} */
export default {
  preprocess: vitePreprocess(),
  kit: {
    // SPA: single index.html fallback, served by the FastAPI static mount at /.
    adapter: adapter({ fallback: "index.html" }),
    alias: { "@engram/contract": contract },
    // Empty for the server-hosted app; set (e.g. /engram/demo) for the static
    // GitHub Pages demo, which lives under a sub-path.
    paths: { base: process.env.ENGRAM_BASE_PATH ?? "" },
  },
};
