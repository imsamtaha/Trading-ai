import { render, screen, waitFor, cleanup } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ServerHealth } from "./server-health";
import { atlasFetch } from "@/lib/api/client";
vi.mock("@/lib/api/client", () => ({
  atlasFetch: vi.fn(), AtlasApiError: class extends Error {}
}));
afterEach(() => { cleanup(); vi.resetAllMocks(); });
describe("server health dashboard", () => {
  it("shows fresh monitor and broker connection separately", async () => {
    vi.mocked(atlasFetch).mockResolvedValue({ server_monitor: {
      state: "ACTIVE", checked_at_utc: "2026-10-01T19:00:00Z",
      components: { backend: { state: "HEALTHY" }, frontend: { state: "HEALTHY" },
        public_route: { state: "HTTPS_REACHABLE" }, mt5: { state: "MT5_OFFLINE" } }
    } });
    render(<ServerHealth language="ar" />);
    expect(await screen.findByText("المراقبة فعّالة")).toBeInTheDocument();
    expect(screen.getByText("MT5: غير متصل")).toBeInTheDocument();
  });
  it("never presents a stale heartbeat as current", async () => {
    vi.mocked(atlasFetch).mockResolvedValue({ server_monitor: {
      state: "STALE", checked_at_utc: "2026-10-01T17:00:00Z", components: {}
    } });
    render(<ServerHealth language="ar" />);
    expect(await screen.findByText("بيانات المراقبة قديمة")).toBeInTheDocument();
  });
  it("hides private monitor when owner endpoint rejects access", async () => {
    vi.mocked(atlasFetch).mockRejectedValue(new Error("Forbidden"));
    const { container } = render(<ServerHealth language="ar" />);
    await waitFor(() => expect(container.textContent).toBe(""));
  });
});

