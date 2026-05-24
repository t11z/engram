export interface Config {
  serverUrl: string;
  token: string;
}

export async function getConfig(): Promise<Config> {
  const stored = await chrome.storage.local.get(["serverUrl", "token"]);
  return {
    serverUrl: typeof stored.serverUrl === "string" ? stored.serverUrl : "",
    token: typeof stored.token === "string" ? stored.token : "",
  };
}

export async function setConfig(config: Config): Promise<void> {
  await chrome.storage.local.set({
    serverUrl: config.serverUrl.trim(),
    token: config.token.trim(),
  });
}

export function isConfigured(config: Config): boolean {
  return config.serverUrl !== "" && config.token !== "";
}
