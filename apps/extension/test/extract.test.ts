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
  /** Chrome the density picker must have excluded (proves it grabbed content). */
  notContains?: string;
}
interface RejectedCase {
  file: string;
  outcome: "rejected";
}
type FixtureCase = SubstantiveCase | RejectedCase;

const cases: FixtureCase[] = [
  { file: "article-blog-post.html", outcome: "substantive", minLen: 400, contains: "the data outlives the tool" },
  { file: "docs-page.html", outcome: "substantive", minLen: 300, contains: "shared secret" },
  // Short content that is essentially the whole page: accepted via coverage,
  // even though it falls well below the strong-length bar.
  { file: "article-short-but-real.html", outcome: "substantive", minLen: 100, contains: "only a hope" },
  // The rendered README is in the DOM amid heavy app chrome (file tree, toolbar,
  // repo header); density scoring must grab the article, not the surrounding
  // navigation (issue #85).
  {
    file: "github-blob-readme.html",
    outcome: "substantive",
    minLen: 300,
    contains: "outlives the tool",
    notContains: "Expand file tree",
  },
  { file: "link-heavy-listing.html", outcome: "rejected" },
  { file: "js-shell-empty-body.html", outcome: "rejected" },
];

describe("extractFromDocument (fixture corpus)", () => {
  it.each(cases)("$file -> $outcome", (testCase) => {
    const result = extractFromDocument(load(testCase.file));

    if (testCase.outcome === "substantive") {
      expect(result.ok).toBe(true);
      if (!result.ok) return; // narrow for TS
      expect(result.markdown.length).toBeGreaterThanOrEqual(testCase.minLen);
      expect(result.markdown).toContain(testCase.contains);
      if (testCase.notContains !== undefined) {
        expect(result.markdown).not.toContain(testCase.notContains);
      }
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

  const shortSentence = "A backup you have never restored is only a hope, not a guarantee.";

  it("accepts a long paragraph on its own (strong length)", () => {
    expect(isSubstantive(prose)).toBe(true);
  });

  it("accepts prose that contains a few inline links", () => {
    const md = `${prose} See [the docs](https://example.com/docs) and [the FAQ](https://example.com/faq).`;
    expect(isSubstantive(md)).toBe(true);
  });

  it("accepts short content that is essentially the whole page (coverage)", () => {
    // Short, but it covers the page's content — a valid clip, not a stub.
    expect(isSubstantive(shortSentence, shortSentence.length)).toBe(true);
  });

  it("rejects short content that is only a small fragment of a larger page", () => {
    // Same short sentence, but the page has far more content we did not capture.
    expect(isSubstantive(shortSentence, 5000)).toBe(false);
  });

  it("rejects a bare link", () => {
    expect(isSubstantive("[GitHub](https://github.com/t11z/engram)")).toBe(false);
  });

  it("rejects a nav-only link list regardless of length", () => {
    const nav = Array.from({ length: 12 }, (_v, i) => `- [Section ${i}](/s/${i})`).join("\n");
    expect(isSubstantive(nav, nav.length)).toBe(false);
  });

  it("rejects empty and near-empty input", () => {
    expect(isSubstantive("")).toBe(false);
    expect(isSubstantive("   \n\n  ")).toBe(false);
    expect(isSubstantive("Too short.")).toBe(false);
  });

  it("honors custom thresholds", () => {
    expect(isSubstantive(shortSentence, 5000)).toBe(false);
    expect(isSubstantive(shortSentence, 5000, { minCoverage: 0 })).toBe(true);
  });
});
