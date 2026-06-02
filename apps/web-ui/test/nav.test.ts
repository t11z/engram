import { describe, expect, it } from "vitest";

import { parse } from "../src/lib/nav";

describe("parse", () => {
  it("defaults view to list", () => {
    expect(parse(new URL("https://x/")).view).toBe("list");
  });

  it("clamps an unknown view to list", () => {
    expect(parse(new URL("https://x/?view=bogus")).view).toBe("list");
  });

  it("reads view/note/q/tag/folder", () => {
    expect(
      parse(new URL("https://x/?view=search&note=1&q=hi&tag=ops&folder=projects&new=1")),
    ).toEqual({
      view: "search",
      note: "1",
      q: "hi",
      tag: "ops",
      folder: "projects",
      compose: true,
    });
  });
});
