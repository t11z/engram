import { Readability } from "@mozilla/readability";

import { htmlToMarkdown } from "@/lib/markdown";
import type { ExtractResponse } from "@/lib/messaging";

/**
 * Pure extraction pipeline, isolated from the WXT content-script wrapper and the
 * `chrome.*` API so it can be unit-tested under jsdom against real Readability.
 *
 * The flow is: Readability first; if its output is not *substantive* (see
 * {@link isSubstantive}) fall back to a de-chromed copy of the body; if neither
 * yields real content, fail honestly instead of saving a link-only stub note.
 */

/**
 * Tuning knobs for {@link isSubstantive}. Defaults are deliberately lenient so we
 * reject obvious stubs (a repo description that is mostly a link, a nav listing)
 * without dropping thin-but-real articles. They are exported so tests can pin the
 * boundary and future contributors can retune against the fixture corpus.
 */
export interface SubstantiveOptions {
  /** Minimum visible (non-link, non-markup) reading characters. */
  minTextChars?: number;
  /** Minimum number of words in the visible reading text. */
  minWords?: number;
  /** Maximum share of visible text that may be link anchor text (0..1). */
  maxLinkDensity?: number;
}

/** ~two sentences. A GitHub repo description is ~50-150 chars and falls below. */
export const DEFAULT_MIN_TEXT_CHARS = 280;
/** A short paragraph; below this it is almost certainly a label/nav/description. */
export const DEFAULT_MIN_WORDS = 50;
/** Above half link-text is a nav/listing/stub, not prose. */
export const DEFAULT_MAX_LINK_DENSITY = 0.5;

/**
 * Decide whether extracted Markdown is real content versus a stub/link/nav.
 *
 * Computed from the Markdown (not the HTML) because the Markdown is exactly what
 * we would save, and its link syntax is trivially parseable without a DOM. The
 * decision is the AND of three independent, cheap signals so a rejection is easy
 * to reason about. No site-specific signals — this stays generic.
 */
export function isSubstantive(markdown: string, opts: SubstantiveOptions = {}): boolean {
  const minTextChars = opts.minTextChars ?? DEFAULT_MIN_TEXT_CHARS;
  const minWords = opts.minWords ?? DEFAULT_MIN_WORDS;
  const maxLinkDensity = opts.maxLinkDensity ?? DEFAULT_MAX_LINK_DENSITY;

  const { text, linkText } = stripMarkup(markdown);
  const textChars = text.length;
  const words = text ? text.split(/\s+/).filter(Boolean).length : 0;
  const linkDensity = textChars > 0 ? linkText.length / textChars : 0;

  return textChars >= minTextChars && words >= minWords && linkDensity <= maxLinkDensity;
}

/**
 * Reduce Markdown to its visible reading text, and separately collect the text
 * that sat inside links, so callers can measure length, word count, and link
 * density. URLs and structural markup are dropped; code and prose text are kept.
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
 * Build the fallback HTML when Readability is missing or too thin: a copy of the
 * document with obvious page chrome removed, narrowed to the main content region
 * if one is present. Pruning the nav/footer plus the link-density gate in
 * {@link isSubstantive} together keep boilerplate from passing as content.
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
    // Readability mutates the document it is given, so hand it a throwaway clone
    // and keep `doc` pristine for the fallback path.
    const article = new Readability(doc.cloneNode(true) as Document).parse() as ParsedArticle | null;

    if (article?.content) {
      const markdown = htmlToMarkdown(article.content);
      if (markdown && isSubstantive(markdown)) {
        return { ok: true, title: pickTitle(doc, article), markdown };
      }
    }

    const fallbackMarkdown = htmlToMarkdown(pickFallbackHtml(doc));
    if (fallbackMarkdown && isSubstantive(fallbackMarkdown)) {
      return { ok: true, title: pickTitle(doc, article), markdown: fallbackMarkdown };
    }

    return { ok: false, error: "Couldn't find readable content to clip on this page." };
  } catch (error) {
    return { ok: false, error: error instanceof Error ? error.message : "Extraction failed." };
  }
}
