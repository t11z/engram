import { defineContentScript } from "wxt/utils/define-content-script";

import { extractFromDocument } from "@/lib/extract";

const EXTRACT_MESSAGE = "engram:extract";

// Injected on demand into the active tab (no static matches). The guard keeps a
// single listener across repeated injections of the same page. Extraction logic
// lives in @/lib/extract so it can be unit-tested without the WXT wrapper.
export default defineContentScript({
  matches: [],
  registration: "runtime",
  main() {
    const flagged = window as unknown as { __engramExtractorReady?: boolean };
    if (flagged.__engramExtractorReady) return;
    flagged.__engramExtractorReady = true;
    chrome.runtime.onMessage.addListener((message: unknown, _sender, sendResponse) => {
      if ((message as { type?: string } | null)?.type === EXTRACT_MESSAGE) {
        sendResponse(extractFromDocument(document));
      }
    });
  },
});
