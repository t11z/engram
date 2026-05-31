import { Readability } from "@mozilla/readability";

import { defineContentScript } from "wxt/utils/define-content-script";

import { htmlToMarkdown } from "@/lib/markdown";
import type { ExtractResponse } from "@/lib/messaging";

const EXTRACT_MESSAGE = "engram:extract";

function extract(): ExtractResponse {
  try {
    const article = new Readability(document.cloneNode(true) as Document).parse();
    const html = article?.content ?? document.body.innerHTML;
    const title = (article?.title || document.title || "Untitled").trim();
    const markdown = htmlToMarkdown(html);
    if (!markdown) {
      return { ok: false, error: "Nothing to clip on this page." };
    }
    return { ok: true, title, markdown };
  } catch (error) {
    return { ok: false, error: error instanceof Error ? error.message : "Extraction failed." };
  }
}

// Injected on demand into the active tab (no static matches). The guard keeps a
// single listener across repeated injections of the same page.
export default defineContentScript({
  matches: [],
  registration: "runtime",
  main() {
    const flagged = window as unknown as { __engramExtractorReady?: boolean };
    if (flagged.__engramExtractorReady) return;
    flagged.__engramExtractorReady = true;
    chrome.runtime.onMessage.addListener((message: unknown, _sender, sendResponse) => {
      if ((message as { type?: string } | null)?.type === EXTRACT_MESSAGE) {
        sendResponse(extract());
      }
    });
  },
});
