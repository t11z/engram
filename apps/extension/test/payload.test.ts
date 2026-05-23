import { describe, expect, it } from "vitest";

import { buildNotePayload } from "@/lib/payload";

describe("buildNotePayload", () => {
  it("builds a NoteCreate with source_url and an idempotency key", () => {
    const payload = buildNotePayload({
      title: "Hello",
      markdown: "# Hello\n\nworld",
      sourceUrl: "https://example.com/a",
    });
    expect(payload.title).toBe("Hello");
    expect(payload.body).toBe("# Hello\n\nworld");
    expect(payload.source_url).toBe("https://example.com/a");
    expect(typeof payload.idempotency_key).toBe("string");
    expect(payload.idempotency_key).toMatch(/[0-9a-f-]{36}/);
  });

  it("uses a fresh idempotency key per call", () => {
    const a = buildNotePayload({ title: "t", markdown: "m", sourceUrl: "https://e.x" });
    const b = buildNotePayload({ title: "t", markdown: "m", sourceUrl: "https://e.x" });
    expect(a.idempotency_key).not.toBe(b.idempotency_key);
  });
});
