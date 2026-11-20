import { afterEach, describe, expect, it, vi } from "vitest";
import { AtlasApiError, atlasFetch } from "@/lib/api/client";

describe("atlasFetch", () => {
  afterEach(() => vi.restoreAllMocks());

  it("returns parsed JSON on success", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ ok: true }), { status: 200 })));
    await expect(atlasFetch("/health")).resolves.toEqual({ ok: true });
  });

  it("throws endpoint-aware error on 503", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("down", { status: 503 })));
    await expect(atlasFetch("/health")).rejects.toMatchObject({ endpoint: "/health", status: 503 });
  });

  it("throws on invalid JSON", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("not-json", { status: 200 })));
    await expect(atlasFetch("/api")).rejects.toBeInstanceOf(AtlasApiError);
  });
});
