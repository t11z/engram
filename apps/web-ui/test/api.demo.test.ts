import { beforeEach, describe, expect, it, vi } from "vitest";

import { seedNotes, seedTrash } from "../src/lib/demo-data";

// Fresh module (and thus a fresh in-memory store) for every test, so mutations
// in one case don't leak into the next.
async function freshApi() {
  vi.resetModules();
  return import("../src/lib/api.demo");
}

let api: Awaited<ReturnType<typeof freshApi>>;

beforeEach(async () => {
  api = await freshApi();
});

describe("demo api (mock store)", () => {
  it("lists all seeded notes, newest first", async () => {
    const res = await api.listNotes();
    expect(res.items).toHaveLength(seedNotes.length);
    expect(res.next_cursor).toBeNull();
    for (let i = 1; i < res.items.length; i++) {
      expect(res.items[i - 1].updated_at >= res.items[i].updated_at).toBe(true);
    }
  });

  it("filters by tag", async () => {
    const res = await api.listNotes({ tag: "coffee" });
    expect(res.items.length).toBeGreaterThan(0);
    expect(res.items.every((n) => (n.tags ?? []).includes("coffee"))).toBe(true);
  });

  it("returns a full note body via getNote", async () => {
    const id = seedNotes[0].id;
    const note = await api.getNote(id);
    expect(note.id).toBe(id);
    expect(note.body).toContain("#");
  });

  it("rejects getNote for an unknown id with a 404", async () => {
    await expect(api.getNote("does-not-exist")).rejects.toMatchObject({ status: 404, code: "not_found" });
  });

  it("searches title and body and ranks title hits higher", async () => {
    const res = await api.search({ q: "coffee" });
    expect(res.items.length).toBeGreaterThan(0);
    expect(res.items[0].snippet).toBeTruthy();
    expect(res.items[0].score).toBeGreaterThanOrEqual(res.items[res.items.length - 1].score);
  });

  it("returns no matches for an empty query", async () => {
    const res = await api.search({ q: "   " });
    expect(res.items).toHaveLength(0);
  });

  it("moves a note to trash on delete and restores it", async () => {
    const id = seedNotes[0].id;
    await api.deleteNote(id);

    const afterDelete = await api.listNotes();
    expect(afterDelete.items.find((n) => n.id === id)).toBeUndefined();

    const trash = await api.listTrash();
    expect(trash.items.find((n) => n.id === id)).toBeDefined();
    expect(trash.items.length).toBe(seedTrash.length + 1);

    const restored = await api.restore(id);
    expect(restored.id).toBe(id);

    const afterRestore = await api.listNotes();
    expect(afterRestore.items.find((n) => n.id === id)).toBeDefined();
    const trashAfter = await api.listTrash();
    expect(trashAfter.items.find((n) => n.id === id)).toBeUndefined();
  });

  it("rejects restore for an unknown id", async () => {
    await expect(api.restore("nope")).rejects.toMatchObject({ status: 404 });
  });
});
