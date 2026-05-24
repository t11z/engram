import type { Config } from "./config";
import type { NoteCreate } from "./payload";
import { apiUrl } from "./url";

export async function saveNote(config: Config, payload: NoteCreate): Promise<void> {
  const res = await fetch(apiUrl(config.serverUrl, "api/v1/notes"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${config.token}`,
    },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    throw new Error(`Save failed: ${res.status}`);
  }
}

export async function testConnection(serverUrl: string, token: string): Promise<boolean> {
  try {
    const res = await fetch(apiUrl(serverUrl, "healthz"), {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    return res.ok;
  } catch {
    return false;
  }
}
