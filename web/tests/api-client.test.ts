import { afterEach, describe, expect, it, vi } from "vitest";
import { AtlasApiError, requestJson } from "../lib/api/client";

afterEach(() => vi.unstubAllGlobals());

describe("requestJson", () => {
  it("preserves endpoint and status for HTTP errors", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("down", { status: 503 })));
    await expect(requestJson("/health")).rejects.toMatchObject({ name: "AtlasApiError", endpoint: "/health", status: 503 });
  });
  it("reports invalid JSON as an API error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("not json", { status: 200 })));
    await expect(requestJson("/api")).rejects.toBeInstanceOf(AtlasApiError);
  });
  it("aborts timed out requests", async () => {
    vi.stubGlobal("fetch", vi.fn((_url: string, init: RequestInit) => new Promise((_resolve, reject) => init.signal?.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError"))))));
    await expect(requestJson("/slow", { timeoutMs: 5 })).rejects.toMatchObject({ name: "AtlasApiError", endpoint: "/slow" });
  });
  it("returns successful JSON", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(Response.json({ status: "ok" })));
    await expect(requestJson("/health")).resolves.toEqual({ status: "ok" });
  });
});
