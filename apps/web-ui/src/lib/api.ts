import type { components } from "@bartleby/contract";

import { currentToken, disconnect } from "./auth";

export type Note = components["schemas"]["Note"];
export type NoteSummary = components["schemas"]["NoteSummary"];
export type NoteListResponse = components["schemas"]["NoteListResponse"];
export type SearchResult = components["schemas"]["SearchResult"];
export type SearchResponse = components["schemas"]["SearchResponse"];

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }

  get isAuth(): boolean {
    return this.status === 401 || this.status === 403;
  }
}

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
  return request(`/notes${query({ cursor: args.cursor, tag: args.tag })}`);
}

export function getNote(id: string): Promise<Note> {
  return request(`/notes/${encodeURIComponent(id)}`);
}

export function deleteNote(id: string): Promise<void> {
  return request(`/notes/${encodeURIComponent(id)}`, { method: "DELETE" });
}

export function search(args: { q: string; tag?: string | null }): Promise<SearchResponse> {
  return request(`/search${query({ q: args.q, tag: args.tag })}`);
}

export function listTrash(args: { cursor?: string } = {}): Promise<NoteListResponse> {
  return request(`/trash${query({ cursor: args.cursor })}`);
}

export function restore(id: string): Promise<Note> {
  return request(`/notes/${encodeURIComponent(id)}/restore`, { method: "POST" });
}
