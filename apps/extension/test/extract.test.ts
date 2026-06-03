import { describe, expect, it } from "vitest";

import { extractFromDocument, isSubstantive } from "@/lib/extract";

// Vite resolves the fixtures at build time, so this works regardless of cwd or
// how the WXT test transform rewrites module URLs.
const fixtures = import.meta.glob("./fixtures/*.html", {
  query: "?raw",
  import: "default",
  eager: true,
}) as Record<string, string>;

function load(file: string): Document {
  const html = fixtures[`./fixtures/${file}`];
  if (html === undefined) throw new Error(`fixture not found: ${file}`);
  return new DOMParser().parseFromString(html, "text/html");
}

/**
 * Labeled fixture corpus. Each real-world page archetype is run through the same
 * pipeline (real @mozilla/readability under jsdom, no network) and asserted by
 * OUTCOME CLASS plus coarse properties — never exact Markdown. New mis-clip
 * reports should be added here as fixtures so they become regression tests.
 */
interface SubstantiveCase {
  file: string;
  outcome: "substantive";
  minLen: number;
  contains: string;
}
interface RejectedCase {
  file: string;
  outcome: "rejected";
}
type FixtureCase = SubstantiveCase | RejectedCase;

const cases: FixtureCase[] = [
  { file: "article-blog-post.html", outcome: "substantive", minLen: 400, contains: "the data outlives the tool" },
  { file: "docs-page.html", outcome: "substantive", minLen: 300, contains: "shared secret" },
  { file: "article-short-but-real.html", outcome: "substantive", minLen: 200, contains: "corruption bug" },
  { file: "github-blob-readme.html", outcome: "rejected" },
  { file: "readability-thin.html", outcome: "rejected" },
  { file: "link-heavy-listing.html", outcome: "rejected" },
  { file: "js-shell-empty-body.html", outcome: "rejected" },
  { file: "paywall-stub.html", outcome: "rejected" },
];

describe("extractFromDocument (fixture corpus)", () => {
  it.each(cases)("$file -> $outcome", (testCase) => {
    const result = extractFromDocument(load(testCase.file));

    if (testCase.outcome === "substantive") {
      expect(result.ok).toBe(true);
      if (!result.ok) return; // narrow for TS
      expect(result.markdown.length).toBeGreaterThanOrEqual(testCase.minLen);
      expect(result.markdown).toContain(testCase.contains);
      expect(isSubstantive(result.markdown)).toBe(true);
      expect(result.title.length).toBeGreaterThan(0);
    } else {
      expect(result.ok).toBe(false);
      if (result.ok) return; // narrow for TS
      expect(result.error).toMatch(/readable content/i);
    }
  });
});

describe("isSubstantive", () => {
  const prose =
    "Plain text files are the most durable format we have for written knowledge because " +
    "every operating system, editor, and programming language already understands them " +
    "without a plugin, a license, or a network connection, which means a note written today " +
    "can still be opened, searched, and copied decades from now even after the original " +
    "application that produced it has long since disappeared.";

  it("accepts a real paragraph of prose", () => {
    expect(isSubstantive(prose)).toBe(true);
  });

  it("accepts prose that contains a few inline links", () => {
    const md = `${prose} See [the docs](https://example.com/docs) and [the FAQ](https://example.com/faq).`;
    expect(isSubstantive(md)).toBe(true);
  });

  it("rejects a bare link", () => {
    expect(isSubstantive("[GitHub](https://github.com/t11z/engram)")).toBe(false);
  });

  it("rejects a nav-only link list", () => {
    expect(isSubstantive("- [Home](/)\n- [About](/about)\n- [Contact](/contact)")).toBe(false);
  });

  it("rejects empty and whitespace-only input", () => {
    expect(isSubstantive("")).toBe(false);
    expect(isSubstantive("   \n\n  ")).toBe(false);
  });

  it("rejects content dominated by link text even when long", () => {
    const linkSoup = Array.from({ length: 12 }, (_v, i) => `[A reasonably long link title number ${i}](https://example.com/${i})`).join(" ");
    expect(isSubstantive(linkSoup)).toBe(false);
  });

  it("rejects text below the word/length floor", () => {
    expect(isSubstantive("A short label with only a handful of words here.")).toBe(false);
  });

  it("honors custom thresholds", () => {
    const short = "Just under twenty words of text that would normally be rejected by the default floor entirely.";
    expect(isSubstantive(short)).toBe(false);
    expect(isSubstantive(short, { minTextChars: 10, minWords: 5 })).toBe(true);
  });
});
