import { get } from "svelte/store";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { deleteNote, getNote, listNotes, restore, search } from "../src/lib/api";
import { connect, disconnect, token } from "../src/lib/auth";

function mockFetch(status: number, body?: unknown) {
  const fetchMock = vi.fn().mockResolvedValue(
    new Response(body === undefined ? null : JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json" },
    }),
  );
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

beforeEach(() => connect("tok"));
afterEach(() => {
  disconnect();
  vi.unstubAllGlobals();
});

describe("api client", () => {
  it("lists notes with bearer header and query", async () => {
    const f = mockFetch(200, { items: [{ id: "1", title: "t", path: "p", updated_at: "u" }], next_cursor: "c" });
    const res = await listNotes({ tag: "ops" });
    const [url, init] = f.mock.calls[0];
    expect(url).toBe("/api/v1/notes?tag=ops");
    expect((init.headers as Record<string, string>).Authorization).toBe("Bearer tok");
    expect(res.items).toHaveLength(1);
    expect(res.next_cursor).toBe("c");
  });

  it("gets a note by path", async () => {
    const f = mockFetch(200, { id: null, title: "t", body: "b", path: "sub/n.md", created_at: "x", updated_at: "y" });
    const note = await getNote("sub/n.md");
    expect(f.mock.calls[0][0]).toBe("/api/v1/notes/by-path/sub/n.md");
    expect(note.body).toBe("b");
  });

  it("deletes a note by path (204 → void)", async () => {
    const f = mockFetch(204);
    await expect(deleteNote("sub/n.md")).resolves.toBeUndefined();
    expect(f.mock.calls[0][0]).toBe("/api/v1/notes/by-path/sub/n.md");
    expect((f.mock.calls[0][1] as RequestInit).method).toBe("DELETE");
  });

  it("searches", async () => {
    mockFetch(200, { items: [{ id: "1", title: "t", path: "p", updated_at: "u", score: 1, snippet: "s" }] });
    const res = await search({ q: "x" });
    expect(res.items[0].snippet).toBe("s");
  });

  it("restores via POST with the path in the body", async () => {
    const f = mockFetch(200, { id: null, title: "t", body: "b", path: "n.md", created_at: "x", updated_at: "y" });
    await restore(".trash/n.md");
    expect(f.mock.calls[0][0]).toBe("/api/v1/notes/restore");
    const init = f.mock.calls[0][1] as RequestInit;
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body as string)).toEqual({ path: ".trash/n.md" });
  });

  it("clears the token and flags auth on 401", async () => {
    mockFetch(401, { error: { code: "unauthorized", message: "no" } });
    await expect(listNotes()).rejects.toMatchObject({ isAuth: true });
    expect(get(token)).toBeNull();
  });

  it("surfaces the error envelope code on 404", async () => {
    mockFetch(404, { error: { code: "not_found", message: "x" } });
    await expect(getNote("1")).rejects.toMatchObject({ status: 404, code: "not_found" });
  });
});
