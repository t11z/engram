import { fileURLToPath } from "node:url";

import { defineConfig } from "wxt";

const contractTypes = fileURLToPath(
  new URL("../../packages/contract/types.ts", import.meta.url),
);

export default defineConfig({
  srcDir: "src",
  manifestVersion: 3,
  // Emit per-browser builds to dist/chrome and dist/firefox (release.yml zips these).
  outDir: "dist",
  outDirTemplate: "{{browser}}",
  // Single alias source for both tsc (baked into .wxt/tsconfig.json) and Vite.
  alias: {
    "@engram/contract": contractTypes,
  },
  vite: () => ({
    build: { sourcemap: true },
  }),
  manifest: {
    // Released artifacts derive their version from the git tag: release.yml sets
    // ENGRAM_EXTENSION_VERSION to the tag (v0.3.0 -> 0.3.0) before building, so the
    // Chrome/Firefox/sources zips always match the GitHub Release. Locally the key
    // is absent, so WXT falls back to package.json. See store/README.md.
    ...(process.env.ENGRAM_EXTENSION_VERSION
      ? { version: process.env.ENGRAM_EXTENSION_VERSION }
      : {}),
    name: "Engram",
    description: "Clip the active tab to Markdown and save it to your Engram server.",
    action: {
      default_icon: {
        "16": "icon/16.png",
        "32": "icon/32.png",
        "48": "icon/48.png",
        "128": "icon/128.png",
      },
    },
    permissions: ["activeTab", "storage", "scripting", "contextMenus"],
    optional_host_permissions: ["*://*/*"],
    browser_specific_settings: {
      gecko: {
        id: "engram@t11z.github.io",
        // Required for new Firefox extensions (AMO, since 2025-11-03). Clipping
        // transmits the page's content to the user's configured server, so we
        // declare websiteContent as a required collection. No telemetry or other
        // data is collected, so there is no optional set. See store/permissions.md.
        data_collection_permissions: {
          required: ["websiteContent"],
        },
      },
    },
  },
});
