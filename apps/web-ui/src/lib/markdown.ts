import DOMPurify from "dompurify";
import { marked } from "marked";

/** Render Markdown to sanitized HTML. Notes are untrusted (clipped pages may
 *  contain HTML/scripts), so the output is always sanitized before use. */
export async function renderMarkdown(body: string): Promise<string> {
  const raw = await marked.parse(body ?? "");
  return DOMPurify.sanitize(raw);
}
