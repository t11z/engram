import type { components } from "@engram/contract";

import { ApiError } from "./api-error";
import { seedNotes, seedTrash } from "./demo-data";

type Note = components["schemas"]["Note"];
type NoteSummary = components["schemas"]["NoteSummary"];
type NoteListResponse = components["schemas"]["NoteListResponse"];
type SearchResult = components["schemas"]["SearchResult"];
type SearchResponse = components["schemas"]["SearchResponse"];

// In-memory store, seeded from the curated dataset. Mutations (delete/restore)
// live for the session only and reset on a full page reload.
let active: Note[] = seedNotes.map((n) => ({ ...n }));
let trash: Note[] = seedTrash.map((n) => ({ ...n }));

const PAGE_SIZE = 50;

/** Simulate a little network latency so loading states are visible. */
function delay<T>(value: T): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), 120));
}

function summary(note: Note): NoteSummary {
  return { id: note.id, path: note.path, tags: note.tags, title: note.title, updated_at: note.updated_at };
}

function byUpdatedDesc(a: Note, b: Note): number {
  return a.updated_at < b.updated_at ? 1 : a.updated_at > b.updated_at ? -1 : 0;
}

function paginate(notes: Note[], cursor?: string): NoteListResponse {
  const start = cursor ? Number(cursor) : 0;
  const page = notes.slice(start, start + PAGE_SIZE);
  const next = start + PAGE_SIZE;
  return {
    items: page.map(summary),
    next_cursor: next < notes.length ? String(next) : null,
  };
}

export function listNotes(args: { cursor?: string; tag?: string | null } = {}): Promise<NoteListResponse> {
  const sorted = [...active].sort(byUpdatedDesc);
  const filtered = args.tag ? sorted.filter((n) => (n.tags ?? []).includes(args.tag as string)) : sorted;
  return delay(paginate(filtered, args.cursor));
}

export function getNote(id: string): Promise<Note> {
  const note = active.find((n) => n.id === id);
  if (!note) {
    return Promise.reject(new ApiError(404, "not_found", "Note not found."));
  }
  return delay({ ...note });
}

export function deleteNote(id: string): Promise<void> {
  const idx = active.findIndex((n) => n.id === id);
  if (idx !== -1) {
    const [note] = active.splice(idx, 1);
    trash = [{ ...note }, ...trash];
  }
  return delay(undefined);
}

export function search(args: { q: string; tag?: string | null }): Promise<SearchResponse> {
  const term = args.q.trim().toLowerCase();
  const pool = args.tag ? active.filter((n) => (n.tags ?? []).includes(args.tag as string)) : active;
  const items: SearchResult[] = pool
    .map((note): SearchResult | null => {
      const haystack = `${note.title}\n${note.body}`;
      const at = haystack.toLowerCase().indexOf(term);
      if (term === "" || at === -1) return null;
      // Higher score for title matches; cheap but plausible relevance.
      const inTitle = note.title.toLowerCase().includes(term);
      return {
        id: note.id,
        path: note.path,
        title: note.title,
        tags: note.tags,
        updated_at: note.updated_at,
        score: inTitle ? 1 : 0.5,
        snippet: snippetAround(note.body, term),
      };
    })
    .filter((r): r is SearchResult => r !== null)
    .sort((a, b) => b.score - a.score);
  return delay({ items });
}

export function listTrash(args: { cursor?: string } = {}): Promise<NoteListResponse> {
  return delay(paginate([...trash].sort(byUpdatedDesc), args.cursor));
}

export function restore(id: string): Promise<Note> {
  const idx = trash.findIndex((n) => n.id === id);
  if (idx === -1) {
    return Promise.reject(new ApiError(404, "not_found", "Note not found."));
  }
  const [note] = trash.splice(idx, 1);
  const restored = { ...note };
  active = [restored, ...active];
  return delay({ ...restored });
}

/** Build a short, single-line snippet centred on the first match in the body. */
function snippetAround(body: string, term: string): string {
  const flat = body.replace(/\s+/g, " ").trim();
  const at = flat.toLowerCase().indexOf(term);
  if (at < 0) return flat.slice(0, 120);
  const start = Math.max(0, at - 40);
  const end = Math.min(flat.length, at + term.length + 60);
  return `${start > 0 ? "…" : ""}${flat.slice(start, end).trim()}${end < flat.length ? "…" : ""}`;
}
