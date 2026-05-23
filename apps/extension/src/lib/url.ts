/** Origin of a server URL, e.g. "https://host:8080/x" -> "https://host:8080". Throws on invalid input. */
export function serverOrigin(serverUrl: string): string {
  return new URL(serverUrl).origin;
}

/** Join a server URL with an API path, tolerating a trailing slash on the base. */
export function apiUrl(serverUrl: string, path: string): string {
  const base = serverUrl.endsWith("/") ? serverUrl : `${serverUrl}/`;
  return new URL(path, base).toString();
}
