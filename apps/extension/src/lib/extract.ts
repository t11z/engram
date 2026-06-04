import { Readability } from "@mozilla/readability";

import { htmlToMarkdown } from "@/lib/markdown";
import type { ExtractResponse } from "@/lib/messaging";

/**
 * Pure extraction pipeline, isolated from the WXT content-script wrapper and the
 * `chrome.*` API so it can be unit-tested under jsdom against real Readability.
 *
 * The job is to grab the page's **visible main content** from the rendered DOM,
 * generically — no per-site logic. The flow: locate the densest readable region of
 * the de-chromed DOM ({@link pickMainContentHtml}); run Readability as a cleaner;
 * keep Readability when it returns substantive content covering that region, else
 * keep the dense region itself; if neither yields real content, fail honestly
 * rather than save a link-only stub note.
 *
 * Why density rather than fixed selectors or Readability alone: app-style pages
 * (e.g. a GitHub file view) wrap the rendered article in heavy navigation chrome —
 * a file tree, a toolbar, breadcrumbs — that a `main`/`article` selector or
 * Readability can mistake for the body. Scoring every candidate by readable
 * (non-link) text length lets the actual content region win wherever it sits.
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

/** Page furniture that is never the main content; removed before scoring. */
const CHROME_SELECTOR =
  "nav, header, footer, aside, script, style, noscript, form, svg," +
  " [role='navigation'], [role='banner'], [role='contentinfo'], [role='complementary']," +
  " [hidden], [aria-hidden='true']";

/**
 * Build the main-content HTML by locating the densest readable region of the
 * de-chromed DOM. Its text also serves as the "page content" denominator for
 * coverage, so that surrounding chrome never penalizes a short but genuine clip.
 *
 * "De-chrome, then score" rather than trust a single selector: after dropping
 * obvious furniture we pick the element that best concentrates readable text (see
 * {@link densestContentElement}). On a plain article that is the `<article>`/`<main>`
 * wrapper; on an app-style page it is the content region sitting amid a file tree
 * or toolbar that a fixed selector would swallow whole.
 */
function pickMainContentHtml(doc: Document): string {
  const clone = doc.cloneNode(true) as Document;
  clone.querySelectorAll(CHROME_SELECTOR).forEach((el) => el.remove());
  const body = clone.body;
  if (!body) return "";
  return (densestContentElement(body) ?? body).innerHTML;
}

/**
 * Among `root` and its container descendants, return the element with the highest
 * readable-text score — its visible text length discounted by how much of that
 * text is link anchors. A clean prose container (much text, few links) outscores
 * both its noisier ancestors (which fold in surrounding chrome) and a nav/listing
 * of the same length (mostly links), so the actual content region wins generically.
 */
function densestContentElement(root: Element): Element | null {
  let best: Element | null = null;
  let bestScore = 0;
  for (const el of [root, ...root.querySelectorAll("article, main, section, div, td, [role='main'], [itemprop]")]) {
    const score = contentScore(el);
    if (score > bestScore) {
      bestScore = score;
      best = el;
    }
  }
  return best;
}

/** Readable-text score for an element: text length × (1 − link density). */
function contentScore(el: Element): number {
  const text = collapse(el.textContent ?? "");
  if (text.length === 0) return 0;
  let linkChars = 0;
  for (const a of el.querySelectorAll("a")) linkChars += collapse(a.textContent ?? "").length;
  const linkDensity = Math.min(linkChars / text.length, 1);
  return text.length * (1 - linkDensity);
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
    // The densest readable region of the rendered DOM is the main content, and
    // its length is the coverage denominator (how much of it a candidate captured).
    const mainMarkdown = htmlToMarkdown(pickMainContentHtml(doc));
    const contentChars = stripMarkup(mainMarkdown).text.length;

    // Readability is a strong cleaner for article pages; prefer it, but only when
    // it returns substantive content that covers most of the region we found —
    // otherwise it has latched onto a fragment and the dense region is truer.
    // Readability mutates the document it is given, so hand it a throwaway clone.
    const article = new Readability(doc.cloneNode(true) as Document).parse() as ParsedArticle | null;

    if (article?.content) {
      const markdown = htmlToMarkdown(article.content);
      if (markdown && isSubstantive(markdown, contentChars)) {
        return { ok: true, title: pickTitle(doc, article), markdown };
      }
    }

    if (mainMarkdown && isSubstantive(mainMarkdown, contentChars)) {
      return { ok: true, title: pickTitle(doc, article), markdown: mainMarkdown };
    }

    return { ok: false, error: "Couldn't find readable content to clip on this page." };
  } catch (error) {
    return { ok: false, error: error instanceof Error ? error.message : "Extraction failed." };
  }
}
