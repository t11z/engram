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
    "@bartleby/contract": contractTypes,
  },
  vite: () => ({
    build: { sourcemap: true },
  }),
  manifest: {
    name: "Bartleby",
    description: "Clip the active tab to Markdown and save it to your Bartleby server.",
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
        id: "bartleby@t11z.github.io",
      },
    },
  },
});
