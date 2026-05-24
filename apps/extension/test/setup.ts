import { fakeBrowser } from "wxt/testing";
import { beforeEach, vi } from "vitest";

// Our code uses the `chrome.*` namespace; point it at WXT's in-memory fake.
vi.stubGlobal("chrome", fakeBrowser);

beforeEach(() => {
  fakeBrowser.reset();
});
