import { afterEach, describe, expect, it, vi } from "vitest";

import { saveNote, testConnection } from "@/lib/api";
import type { NoteCreate } from "@/lib/payload";

const config = { serverUrl: "https://h", token: "tok" };
const payload: NoteCreate = {
  title: "t",
  body: "b",
  source_url: "https://e.x",
  idempotency_key: "k",
};

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("saveNote", () => {
  it("POSTs to /api/v1/notes with auth and JSON body", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 201 }));
    vi.stubGlobal("fetch", fetchMock);

    await saveNote(config, payload);

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("https://h/api/v1/notes");
    expect(init.method).toBe("POST");
    expect(init.headers.Authorization).toBe("Bearer tok");
    expect(init.headers["Content-Type"]).toBe("application/json");
    expect(JSON.parse(init.body)).toEqual(payload);
  });

  it("throws on a non-2xx response", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 401 })));
    await expect(saveNote(config, payload)).rejects.toThrow(/401/);
  });
});

describe("testConnection", () => {
  it("returns true on a 200 from /healthz", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    expect(await testConnection("https://h", "tok")).toBe(true);
    expect(fetchMock.mock.calls[0][0]).toBe("https://h/healthz");
  });

  it("returns false on error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 500 })));
    expect(await testConnection("https://h", "tok")).toBe(false);
  });
});
