import { defineBackground } from "wxt/utils/define-background";

import { saveNote } from "@/lib/api";
import { setError, setSuccess, scheduleClear } from "@/lib/badge";
import { getConfig, isConfigured } from "@/lib/config";
import type { ExtractResponse } from "@/lib/messaging";
import { buildNotePayload } from "@/lib/payload";

const EXTRACTOR_FILE = "content-scripts/extractor.js";
const EXTRACT_MESSAGE = "bartleby:extract";

async function clip(tab: chrome.tabs.Tab): Promise<void> {
  try {
    if (tab.id === undefined || !tab.url) return;
    const config = await getConfig();
    if (!isConfigured(config)) {
      await chrome.runtime.openOptionsPage();
      await setError();
      scheduleClear();
      return;
    }
    // activeTab grants access to this tab for this user gesture.
    await chrome.scripting.executeScript({ target: { tabId: tab.id }, files: [EXTRACTOR_FILE] });
    const result = (await chrome.tabs.sendMessage(tab.id, {
      type: EXTRACT_MESSAGE,
    })) as ExtractResponse;
    if (!result?.ok) {
      await setError();
      scheduleClear();
      return;
    }
    await saveNote(
      config,
      buildNotePayload({ title: result.title, markdown: result.markdown, sourceUrl: tab.url }),
    );
    await setSuccess();
    scheduleClear();
  } catch {
    await setError();
    scheduleClear();
  }
}

export default defineBackground(() => {
  chrome.action.onClicked.addListener((tab) => {
    void clip(tab);
  });
});
