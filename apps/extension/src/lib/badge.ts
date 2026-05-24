const CLEAR_AFTER_MS = 4000;

export async function setSuccess(): Promise<void> {
  await chrome.action.setBadgeBackgroundColor({ color: "#1a7f37" });
  await chrome.action.setBadgeText({ text: "OK" });
}

export async function setError(): Promise<void> {
  await chrome.action.setBadgeBackgroundColor({ color: "#cf222e" });
  await chrome.action.setBadgeText({ text: "ERR" });
}

export async function clearBadge(): Promise<void> {
  await chrome.action.setBadgeText({ text: "" });
}

export function scheduleClear(): void {
  setTimeout(() => {
    void clearBadge();
  }, CLEAR_AFTER_MS);
}
