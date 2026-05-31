import { testConnection } from "@/lib/api";
import { getConfig, setConfig } from "@/lib/config";
import { serverOrigin } from "@/lib/url";

const serverUrlInput = document.querySelector<HTMLInputElement>("#serverUrl")!;
const tokenInput = document.querySelector<HTMLInputElement>("#token")!;
const status = document.querySelector<HTMLDivElement>("#status")!;

function show(message: string, kind: "ok" | "err" | "neutral" = "neutral"): void {
  status.textContent = message;
  status.classList.remove("ok", "err");
  if (kind !== "neutral") status.classList.add(kind);
}

async function load(): Promise<void> {
  const config = await getConfig();
  serverUrlInput.value = config.serverUrl;
  tokenInput.value = config.token;
}

async function onSave(): Promise<void> {
  const serverUrl = serverUrlInput.value.trim();
  const token = tokenInput.value.trim();
  let origin: string;
  try {
    origin = serverOrigin(serverUrl);
  } catch {
    show("Enter a valid server URL (including https://).", "err");
    return;
  }
  const granted = await chrome.permissions.request({ origins: [`${origin}/*`] });
  if (!granted) {
    show("Host permission denied — the extension can't reach that server.", "err");
    return;
  }
  await setConfig({ serverUrl, token });
  show("Saved.", "ok");
}

async function onTest(): Promise<void> {
  show("Testing…");
  const ok = await testConnection(serverUrlInput.value.trim(), tokenInput.value.trim());
  show(ok ? "Connected." : "No response from server.", ok ? "ok" : "err");
}

document.querySelector("#save")!.addEventListener("click", () => void onSave());
document.querySelector("#test")!.addEventListener("click", () => void onTest());
void load();
