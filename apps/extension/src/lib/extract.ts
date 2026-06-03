import { Readability } from "@mozilla/readability";

import { htmlToMarkdown } from "@/lib/markdown";
import type { ExtractResponse } from "@/lib/messaging";

/**
 * Pure extraction pipeline, isolated from the WXT content-script wrapper and the
 * `chrome.*` API so it can be unit-tested under jsdom against real Readability.
 *
 * The flow is: Readability first; if its output is only a small fragment of the
 * page's actual content, prefer a de-chromed copy of the body instead; if neither
 * yields real content, fail honestly rather than save a link-only stub note.
 */

/**
 * Tuning knobs for {@link isSubstantive}. The guard deliberately does **not**
 * reject content merely for being short: a definition, a quote, a short note, or
 * a code snippet is valid even at a handful of words. It rejects only content
 * that is empty, link/nav-dominated, or a small fragment of a much larger body
 * (which signals we missed the real content). All knobs are exported so tests
 * can pin the boundaries and contributors can retune against the fixture corpus.
 */
export interface SubstantiveOptions {
  /** Length at which content is accepted on its own, regardless of coverage. */
  minStrongChars?: number;
  /** Floor below which content is treated as effectively empty. */
  minAbsoluteChars?: number;
  /** Maximum share of visible text that may be link anchor text (0..1). */
  maxLinkDensity?: number;
  /** For short content, the minimum share of the page's content it must cover. */
  minCoverage?: number;
}

/** ~two sentences: clearly a real body, accepted without a coverage check. */
export const DEFAULT_MIN_STRONG_CHARS = 280;
/** Below this there is essentially nothing to clip (≈ a handful of words). */
export const DEFAULT_MIN_ABSOLUTE_CHARS = 40;
/** Above half link-text is a nav/listing/stub, not prose. */
export const DEFAULT_MAX_LINK_DENSITY = 0.5;
/** A short clip is genuine when it covers at least this share of page content. */
export const DEFAULT_MIN_COVERAGE = 0.5;

/**
 * Decide whether extracted Markdown is real content versus a stub/link/nav.
 *
 * Computed from the Markdown (its link syntax is trivially parseable without a
 * DOM). The decision, in order: reject the effectively-empty; reject the
 * link-dominated; accept anything substantial on its own; otherwise accept short
 * content only when it covers a meaningful share of `pageContentChars` — the
 * length of the page's de-chromed content. That last rule is what lets a short
 * but genuine clip through (it *is* the page) while rejecting a short fragment of
 * a much larger body (we missed the bulk). No site-specific signals.
 *
 * @param pageContentChars Length of the page's de-chromed content text. When
 *   omitted, the Markdown is treated as the whole content (coverage = 1).
 */
export function isSubstantive(
  markdown: string,
  pageContentChars?: number,
  opts: SubstantiveOptions = {},
): boolean {
  const minStrong = opts.minStrongChars ?? DEFAULT_MIN_STRONG_CHARS;
  const minAbsolute = opts.minAbsoluteChars ?? DEFAULT_MIN_ABSOLUTE_CHARS;
  const maxLinkDensity = opts.maxLinkDensity ?? DEFAULT_MAX_LINK_DENSITY;
  const minCoverage = opts.minCoverage ?? DEFAULT_MIN_COVERAGE;

  const { text, linkText } = stripMarkup(markdown);
  const textChars = text.length;

  if (textChars < minAbsolute) return false;
  if (linkText.length / textChars > maxLinkDensity) return false;
  if (textChars >= minStrong) return true;

  const denominator = Math.max(pageContentChars ?? textChars, 1);
  return textChars / denominator >= minCoverage;
}

/**
 * Reduce Markdown to its visible reading text, and separately collect the text
 * that sat inside links, so callers can measure length and link density. URLs and
 * structural markup are dropped; code and prose text are kept.
 */
function stripMarkup(markdown: string): { text: string; linkText: string } {
  let linkText = "";
  let s = markdown;

  // Drop image syntax entirely (alt text is rarely reading content).
  s = s.replace(/!\[[^\]]*\]\([^)]*\)/g, " ");
  // Inline links [text](url) -> text; remember the anchor text for link density.
  s = s.replace(/\[([^\]]*)\]\([^)]*\)/g, (_m, t: string) => {
    linkText += ` ${t}`;
    return t;
  });
  // Autolinks <https://…> and any bare URLs.
  s = s.replace(/<https?:\/\/[^>]+>/gi, " ");
  s = s.replace(/https?:\/\/\S+/gi, " ");
  // Code fences (keep the code text, drop the fence markers).
  s = s.replace(/```+/g, " ");

  return { text: collapse(stripChars(s)), linkText: collapse(stripChars(linkText)) };
}

/** Remove Markdown structural characters that are not reading content. */
function stripChars(s: string): string {
  return s.replace(/[#*_~`>|]/g, " ");
}

/** Collapse runs of whitespace and trim. */
function collapse(s: string): string {
  return s.replace(/\s+/g, " ").trim();
}

/**
 * Build the fallback HTML: a copy of the document with obvious page chrome
 * removed, narrowed to the main content region if one is present. Its text also
 * serves as the "page content" denominator for coverage, so that surrounding
 * nav/footer chrome never penalizes a short but genuine clip.
 */
function pickFallbackHtml(doc: Document): string {
  const clone = doc.cloneNode(true) as Document;
  clone
    .querySelectorAll(
      "nav, header, footer, aside, script, style, noscript, form," +
        " [role='navigation'], [role='banner'], [role='contentinfo']",
    )
    .forEach((el) => el.remove());

  const root =
    firstWithText(clone, "main") ??
    firstWithText(clone, "[role='main']") ??
    firstWithText(clone, "article") ??
    clone.body;

  return root?.innerHTML ?? "";
}

/** First element matching `selector` that has non-whitespace text, if any. */
function firstWithText(root: Document, selector: string): Element | null {
  for (const el of root.querySelectorAll(selector)) {
    if (el.textContent && el.textContent.trim()) return el;
  }
  return null;
}

interface ParsedArticle {
  title?: string | null;
  content?: string | null;
}

function pickTitle(doc: Document, article: ParsedArticle | null): string {
  return (article?.title || doc.title || "Untitled").trim();
}

/** Run the full extraction pipeline against a document. DOM in, response out. */
export function extractFromDocument(doc: Document): ExtractResponse {
  try {
    // The de-chromed body is both the fallback candidate and the coverage
    // denominator (how much of the page's content a candidate captured).
    const fallbackMarkdown = htmlToMarkdown(pickFallbackHtml(doc));
    const contentChars = stripMarkup(fallbackMarkdown).text.length;

    // Readability mutates the document it is given, so hand it a throwaway clone
    // and keep `doc` pristine.
    const article = new Readability(doc.cloneNode(true) as Document).parse() as ParsedArticle | null;

    if (article?.content) {
      const markdown = htmlToMarkdown(article.content);
      if (markdown && isSubstantive(markdown, contentChars)) {
        return { ok: true, title: pickTitle(doc, article), markdown };
      }
    }

    if (fallbackMarkdown && isSubstantive(fallbackMarkdown, contentChars)) {
      return { ok: true, title: pickTitle(doc, article), markdown: fallbackMarkdown };
    }

    return { ok: false, error: "Couldn't find readable content to clip on this page." };
  } catch (error) {
    return { ok: false, error: error instanceof Error ? error.message : "Extraction failed." };
  }
}
