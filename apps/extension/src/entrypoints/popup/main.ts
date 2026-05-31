import { getConfig, isConfigured } from "../../lib/config";
import { saveNote, testConnection } from "../../lib/api";
import { buildNotePayload } from "../../lib/payload";

interface TabInfo {
  title: string;
  url: string;
}

async function getCurrentTab(): Promise<TabInfo> {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  return {
    title: tab?.title ?? "Untitled",
    url: tab?.url ?? "",
  };
}

function setStatus(state: "online" | "offline" | "checking", text: string): void {
  const pill = document.getElementById("status-pill")!;
  const label = document.getElementById("status-text")!;
  pill.className = `status-pill status-${state}`;
  label.textContent = text;
}

function showError(msg: string): void {
  const el = document.getElementById("error-msg")!;
  el.textContent = msg;
  el.classList.add("visible");
  setTimeout(() => el.classList.remove("visible"), 4000);
}

function showConfirm(note: string): void {
  document.getElementById("main-content")!.style.display = "none";
  const confirmState = document.getElementById("confirm-state")!;
  confirmState.classList.add("visible");
  document.getElementById("confirm-sub")!.textContent = note;
  setTimeout(() => window.close(), 1800);
}

async function main(): Promise<void> {
  const config = await getConfig();

  if (!isConfigured(config)) {
    document.getElementById("setup-prompt")!.classList.add("visible");
    document.getElementById("btn-open-options")?.addEventListener("click", () => {
      chrome.runtime.openOptionsPage();
    });
    setStatus("offline", "not configured");
    return;
  }

  document.getElementById("main-content")!.style.display = "block";

  // Check vault connection
  const connected = await testConnection(config.serverUrl, config.token);
  setStatus(connected ? "online" : "offline", connected ? "vault online" : "unreachable");

  // Load current tab
  const tab = await getCurrentTab();
  const titleEl = document.getElementById("page-title")!;
  const urlEl = document.getElementById("page-url")!;
  titleEl.textContent = tab.title;
  urlEl.textContent = tab.url;

  // Tags
  const tags: string[] = [];
  const tagsRow = document.getElementById("tags-row")!;
  const btnAddTag = document.getElementById("btn-add-tag")!;

  function addTagChip(tag: string): void {
    const chip = document.createElement("span");
    chip.className = "tag-chip";
    chip.textContent = `#${tag}`;
    chip.title = "Click to remove";
    chip.addEventListener("click", () => {
      const i = tags.indexOf(tag);
      if (i > -1) tags.splice(i, 1);
      chip.remove();
    });
    tagsRow.insertBefore(chip, btnAddTag);
  }

  btnAddTag.addEventListener("click", () => {
    const input = prompt("Add tag:");
    if (input?.trim()) {
      const tag = input.trim().replace(/^#/, "");
      if (!tags.includes(tag)) {
        tags.push(tag);
        addTagChip(tag);
      }
    }
  });

  // Open vault
  document.getElementById("btn-open-vault")?.addEventListener("click", () => {
    chrome.tabs.create({ url: config.serverUrl });
  });

  // Save
  const btnSave = document.getElementById("btn-save") as HTMLButtonElement;
  btnSave.addEventListener("click", async () => {
    if (!connected) {
      showError("Couldn't reach the vault. Check that the server is running.");
      return;
    }
    const noteText = (document.getElementById("note-field") as HTMLTextAreaElement).value;
    btnSave.disabled = true;
    btnSave.textContent = "Saving…";
    try {
      const body = [noteText.trim(), `\n\n---\nSource: ${tab.url}`].filter(Boolean).join("\n\n");
      const payload = buildNotePayload({
        title: tab.title,
        markdown: body,
        sourceUrl: tab.url,
      });
      // Attach tags if API supports them
      const payloadWithTags = tags.length ? { ...payload, tags } : payload;
      await saveNote(config, payloadWithTags as Parameters<typeof saveNote>[1]);
      showConfirm("1 note · indexed");
    } catch (e) {
      btnSave.disabled = false;
      btnSave.textContent = "Add to Engram";
      showError(e instanceof Error ? e.message : "Save failed.");
    }
  });
}

document.addEventListener("DOMContentLoaded", () => {
  void main();
});
