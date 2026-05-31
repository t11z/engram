import { fileURLToPath } from "node:url";

import { svelte } from "@sveltejs/vite-plugin-svelte";
import { defineConfig } from "vitest/config";

const contract = fileURLToPath(new URL("../../packages/contract/types.ts", import.meta.url));
const appNavigation = fileURLToPath(new URL("./test/stubs/app-navigation.ts", import.meta.url));

export default defineConfig({
  plugins: [svelte()],
  resolve: {
    alias: {
      "@engram/contract": contract,
      "$app/navigation": appNavigation,
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
  },
});
