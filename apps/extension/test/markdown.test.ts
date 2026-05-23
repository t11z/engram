import { describe, expect, it } from "vitest";

import { htmlToMarkdown } from "@/lib/markdown";

describe("htmlToMarkdown", () => {
  it("converts headings, paragraphs, and links", () => {
    const md = htmlToMarkdown("<h1>Title</h1><p>Hello <a href='https://e.x'>link</a></p>");
    expect(md).toContain("# Title");
    expect(md).toContain("[link](https://e.x)");
  });

  it("uses fenced code blocks", () => {
    const md = htmlToMarkdown("<pre><code>console.log(1)</code></pre>");
    expect(md).toContain("```");
  });

  it("trims surrounding whitespace", () => {
    expect(htmlToMarkdown("<p>x</p>")).toBe("x");
  });
});
