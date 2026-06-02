import type { components } from "@engram/contract";

import * as demo from "./api.demo";
import { ApiError } from "./api-error";
import { currentToken, disconnect } from "./auth";
import { DEMO } from "./demo";

export { ApiError };

export type Note = components["schemas"]["Note"];
export type NoteSummary = components["schemas"]["NoteSummary"];
export type NoteListResponse = components["schemas"]["NoteListResponse"];
export type SearchResult = components["schemas"]["SearchResult"];
export type SearchResponse = components["schemas"]["SearchResponse"];
export type OutgoingLink = components["schemas"]["OutgoingLink"];
export type GraphView = components["schemas"]["GraphView"];
export type TagCount = components["schemas"]["TagCount"];

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const tok = currentToken();
  const res = await fetch(`/api/v1${path}`, {
    ...init,
    headers: {
      ...(init.headers ?? {}),
      ...(tok ? { Authorization: `Bearer ${tok}` } : {}),
    },
  });
  if (res.status === 401 || res.status === 403) {
    disconnect();
    throw new ApiError(res.status, res.status === 401 ? "unauthorized" : "forbidden", "Session ended.");
  }
  if (res.status === 204) {
    return undefined as T;
  }
  const body = await res.json().catch(() => null);
  if (!res.ok) {
    const error = (body as { error?: { code?: string; message?: string } } | null)?.error;
    throw new ApiError(res.status, error?.code ?? "error", error?.message ?? `Request failed (${res.status}).`);
  }
  return body as T;
}

function query(params: Record<string, string | null | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value != null && value !== "") search.set(key, value);
  }
  const out = search.toString();
  return out ? `?${out}` : "";
}

export function listNotes(args: { cursor?: string; tag?: string | null } = {}): Promise<NoteListResponse> {
  if (DEMO) return demo.listNotes(args);
  return request(`/notes${query({ cursor: args.cursor, tag: args.tag })}`);
}

// Encode each path segment but keep the slashes, so nested paths address the
// `/notes/by-path/{path:path}` route without %2F (which proxies often reject).
function encodePath(path: string): string {
  return path.split("/").map(encodeURIComponent).join("/");
}

export function getNote(path: string): Promise<Note> {
  if (DEMO) return demo.getNote(path);
  return request(`/notes/by-path/${encodePath(path)}`);
}

export function deleteNote(path: string): Promise<void> {
  if (DEMO) return demo.deleteNote(path);
  return request(`/notes/by-path/${encodePath(path)}`, { method: "DELETE" });
}

export function search(args: { q: string; tag?: string | null }): Promise<SearchResponse> {
  if (DEMO) return demo.search(args);
  return request(`/search${query({ q: args.q, tag: args.tag })}`);
}

export function listTrash(args: { cursor?: string } = {}): Promise<NoteListResponse> {
  if (DEMO) return demo.listTrash(args);
  return request(`/trash${query({ cursor: args.cursor })}`);
}

export function getBacklinks(path: string): Promise<NoteListResponse> {
  if (DEMO) return demo.getBacklinks(path);
  return request(`/backlinks${query({ path })}`);
}

export function getRelated(path: string): Promise<NoteListResponse> {
  if (DEMO) return demo.getRelated(path);
  return request(`/related${query({ path })}`);
}

export function getLinks(path: string): Promise<OutgoingLink[]> {
  if (DEMO) return demo.getLinks(path);
  return request(`/links${query({ path })}`);
}

export function getGraph(path: string, depth = 1): Promise<GraphView> {
  if (DEMO) return demo.getGraph(path, depth);
  return request(`/graph${query({ path, depth: String(depth) })}`);
}

export function listFolders(): Promise<string[]> {
  if (DEMO) return demo.listFolders();
  return request(`/folders`);
}

export function listTags(): Promise<TagCount[]> {
  if (DEMO) return demo.listTags();
  return request(`/tags`);
}

export function restore(path: string): Promise<Note> {
  if (DEMO) return demo.restore(path);
  return request(`/notes/restore`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path }),
  });
}
