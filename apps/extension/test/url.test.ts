import { describe, expect, it } from "vitest";

import { apiUrl, serverLinkUrl, serverOrigin } from "@/lib/url";

describe("serverOrigin", () => {
  it("extracts the origin", () => {
    expect(serverOrigin("https://host:8080/x")).toBe("https://host:8080");
  });
  it("throws on invalid input", () => {
    expect(() => serverOrigin("not a url")).toThrow();
  });
});

describe("serverLinkUrl", () => {
  it("returns the origin for a valid server URL", () => {
    expect(serverLinkUrl("https://host:8080/x")).toBe("https://host:8080");
    expect(serverLinkUrl("https://host:8080/")).toBe("https://host:8080");
  });
  it("returns null when unset or invalid", () => {
    expect(serverLinkUrl("")).toBeNull();
    expect(serverLinkUrl("not a url")).toBeNull();
  });
});

describe("apiUrl", () => {
  it("joins path, tolerating a trailing slash", () => {
    expect(apiUrl("https://h", "api/v1/notes")).toBe("https://h/api/v1/notes");
    expect(apiUrl("https://h/", "api/v1/notes")).toBe("https://h/api/v1/notes");
  });
});
