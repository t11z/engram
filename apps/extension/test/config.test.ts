import { describe, expect, it } from "vitest";

import { getConfig, isConfigured, setConfig } from "@/lib/config";

describe("config", () => {
  it("defaults to empty strings when unset", async () => {
    const config = await getConfig();
    expect(config).toEqual({ serverUrl: "", token: "" });
  });

  it("round-trips and trims", async () => {
    await setConfig({ serverUrl: "  https://h  ", token: "  tok  " });
    expect(await getConfig()).toEqual({ serverUrl: "https://h", token: "tok" });
  });

  it("isConfigured requires both fields", () => {
    expect(isConfigured({ serverUrl: "", token: "" })).toBe(false);
    expect(isConfigured({ serverUrl: "https://h", token: "" })).toBe(false);
    expect(isConfigured({ serverUrl: "https://h", token: "t" })).toBe(true);
  });
});
