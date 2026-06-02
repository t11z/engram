import DOMPurify from "dompurify";
import { marked } from "marked";

const WIKILINK = /(?<!!)\[\[([^\]\n]+)\]\]/g;

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/** Turn `[[target|alias]]` into a clickable anchor carrying the raw target in a
 *  data attribute; MarkdownView resolves the target and navigates on click. */
function linkifyWikilinks(body: string): string {
  return body.replace(WIKILINK, (_match, inner: string) => {
    const target = inner.split("|")[0].split("#")[0].trim();
    const alias = inner.includes("|") ? inner.slice(inner.indexOf("|") + 1).trim() : inner.trim();
    if (!target) return _match;
    return `<a class="wikilink" data-target="${escapeHtml(target)}">${escapeHtml(alias)}</a>`;
  });
}

/** Render Markdown to sanitized HTML. Notes are untrusted (clipped pages may
 *  contain HTML/scripts), so the output is always sanitized before use.
 *  `[[wikilinks]]` are rendered as clickable anchors unless disabled. */
export async function renderMarkdown(
  body: string,
  options: { wikilinks?: boolean } = {},
): Promise<string> {
  const source = options.wikilinks === false ? (body ?? "") : linkifyWikilinks(body ?? "");
  const raw = await marked.parse(source);
  return DOMPurify.sanitize(raw, { ADD_ATTR: ["data-target"] });
}
