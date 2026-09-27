import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AtlasAppShell } from "@/app/atlas-app-shell";
afterEach(() => vi.unstubAllGlobals());
describe("live dashboard availability", () => {
  it("shows degraded when health succeeds but account telemetry is absent", async () => {
    vi.stubGlobal("fetch", vi.fn((path: string) => Promise.resolve(new Response(JSON.stringify(
      path.endsWith("/health") ? { status: "healthy" } : path.includes("chart-data") ? { candles: [] } : { status: "ONLINE" }
    ), { status: 200 }))));
    render(<AtlasAppShell />);
    await waitFor(() => expect(screen.getByText("Backend degraded")).toBeInTheDocument());
    expect(screen.getByText("Backend offline")).toBeInTheDocument();
  });
});
