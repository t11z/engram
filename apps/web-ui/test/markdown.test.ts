import { describe, expect, it } from "vitest";

import { renderMarkdown } from "../src/lib/markdown";

describe("renderMarkdown", () => {
  it("renders Markdown to HTML", async () => {
    expect(await renderMarkdown("# Title")).toContain("<h1");
  });

  it("strips <script>", async () => {
    const html = await renderMarkdown("<script>alert(1)</script> ok");
    expect(html).not.toContain("<script");
  });

  it("strips event-handler attributes", async () => {
    const html = await renderMarkdown("<img src=x onerror=alert(1)>");
    expect(html).not.toContain("onerror");
  });

  it("strips javascript: links", async () => {
    const html = await renderMarkdown("[x](javascript:alert(1))");
    expect(html).not.toContain("javascript:");
  });
});
