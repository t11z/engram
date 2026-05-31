import type { components } from "@engram/contract";

export type NoteCreate = components["schemas"]["NoteCreate"];

export interface ClipInput {
  title: string;
  markdown: string;
  sourceUrl: string;
}

/** Build the POST body for /api/v1/notes. A fresh idempotency key makes the
 *  single POST retry-safe while allowing intentional re-clips of the same page. */
export function buildNotePayload(input: ClipInput): NoteCreate {
  return {
    title: input.title,
    body: input.markdown,
    source_url: input.sourceUrl,
    idempotency_key: crypto.randomUUID(),
  };
}
