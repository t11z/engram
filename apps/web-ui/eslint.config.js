import js from "@eslint/js";
import svelte from "eslint-plugin-svelte";
import globals from "globals";
import tseslint from "typescript-eslint";

export default tseslint.config(
  { ignores: [".svelte-kit/**", "build/**", "node_modules/**"] },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  ...svelte.configs["flat/recommended"],
  {
    files: ["**/*.svelte"],
    languageOptions: { parserOptions: { parser: tseslint.parser } },
    // Bare reactive reads inside $effect are the Svelte 5 idiom for tracking deps.
    rules: { "@typescript-eslint/no-unused-expressions": "off" },
  },
  {
    languageOptions: { globals: { ...globals.browser } },
    // We navigate via query strings and link to external source URLs.
    rules: { "svelte/no-navigation-without-resolve": "off" },
  },
);
