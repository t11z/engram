import { defineBackground } from "wxt/utils/define-background";

import { saveNote } from "@/lib/api";
import { setError, setSuccess, scheduleClear } from "@/lib/badge";
import { getConfig, isConfigured } from "@/lib/config";
import type { ExtractResponse } from "@/lib/messaging";
import { buildNotePayload } from "@/lib/payload";
import { serverLinkUrl } from "@/lib/url";

const EXTRACTOR_FILE = "content-scripts/extractor.js";
const EXTRACT_MESSAGE = "bartleby:extract";
const OPEN_SERVER_MENU_ID = "bartleby:open-server";

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

async function openServer(): Promise<void> {
  const config = await getConfig();
  const url = serverLinkUrl(config.serverUrl);
  if (!url) {
    await chrome.runtime.openOptionsPage();
    return;
  }
  await chrome.tabs.create({ url });
}

export default defineBackground(() => {
  chrome.runtime.onInstalled.addListener(() => {
    chrome.contextMenus.create({
      id: OPEN_SERVER_MENU_ID,
      title: "Open Bartleby server",
      contexts: ["action"],
    });
  });

  chrome.contextMenus.onClicked.addListener((info) => {
    if (info.menuItemId === OPEN_SERVER_MENU_ID) void openServer();
  });

  chrome.action.onClicked.addListener((tab) => {
    void clip(tab);
  });
});
