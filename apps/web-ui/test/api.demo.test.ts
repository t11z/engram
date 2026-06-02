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
    const path = seedNotes[0].path;
    const note = await api.getNote(path);
    expect(note.path).toBe(path);
    expect(note.body).toContain("#");
  });

  it("rejects getNote for an unknown path with a 404", async () => {
    await expect(api.getNote("does-not-exist.md")).rejects.toMatchObject({
      status: 404,
      code: "not_found",
    });
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
    const path = seedNotes[0].path;
    const trashPath = `.trash/${path}`;
    await api.deleteNote(path);

    const afterDelete = await api.listNotes();
    expect(afterDelete.items.find((n) => n.path === path)).toBeUndefined();

    const trash = await api.listTrash();
    expect(trash.items.find((n) => n.path === trashPath)).toBeDefined();
    expect(trash.items.length).toBe(seedTrash.length + 1);

    const restored = await api.restore(trashPath);
    expect(restored.path).toBe(path);

    const afterRestore = await api.listNotes();
    expect(afterRestore.items.find((n) => n.path === path)).toBeDefined();
    const trashAfter = await api.listTrash();
    expect(trashAfter.items.find((n) => n.path === trashPath)).toBeUndefined();
  });

  it("rejects restore for an unknown path", async () => {
    await expect(api.restore(".trash/nope.md")).rejects.toMatchObject({ status: 404 });
  });

  it("resolves the seeded wikilink for links, backlinks, tags, and folders", async () => {
    const sourdough = seedNotes[0].path;
    const pourOver = seedNotes[1].path;

    const links = await api.getLinks(sourdough);
    expect(links.some((l) => l.resolved_path === pourOver)).toBe(true);

    const backlinks = await api.getBacklinks(pourOver);
    expect(backlinks.items.some((i) => i.path === sourdough)).toBe(true);

    const tags = await api.listTags();
    expect(tags.some((t) => t.tag === "kitchen")).toBe(true); // inline #kitchen

    const folders = await api.listFolders();
    expect(folders).toContain("2026");

    const graph = await api.getGraph(sourdough, 1);
    expect((graph.nodes ?? []).some((n) => n.path === pourOver)).toBe(true);
  });
});
