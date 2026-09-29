import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DashboardScreen } from "@/features/dashboard/dashboard-screen";
import { DASHBOARD_FIXTURE } from "@/lib/api/fixtures";

describe("DashboardScreen", () => {
  it("renders account and market telemetry", () => {
    render(<DashboardScreen state={DASHBOARD_FIXTURE} briefingAvailable headlines={[{ title: "Rates update", url: "https://example.com/news" }]} />);
    expect(screen.getByRole("heading", { level: 1, name: "ATLAS" })).toBeInTheDocument();
    expect(screen.getByText("Trading Intelligence")).toHaveClass("atlas-brand-subtitle");
    expect(screen.queryByText(/ATLAS intelligence/i)).not.toBeInTheDocument();
    expect(screen.getByText("10,000.00")).toBeInTheDocument();
    expect(screen.getByText("10,248.42")).toBeInTheDocument();
    expect(screen.getByText("EURUSD")).toBeInTheDocument();
    expect(screen.getAllByText("XAUUSD").length).toBeGreaterThan(0);
    expect(document.getElementById("analytics")).toBeInTheDocument();
    expect(document.getElementById("news")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Rates update" })).toHaveAttribute("href", "https://example.com/news");
  });

  it("shows chart levels only for the selected matching position", () => {
    const { rerender } = render(<DashboardScreen state={DASHBOARD_FIXTURE} symbol="BTCUSDT" />);
    expect(screen.getByText("Entry 66,420")).toBeInTheDocument();
    rerender(<DashboardScreen state={DASHBOARD_FIXTURE} symbol="XAUUSD" />);
    expect(screen.queryByText("Entry 66,420")).not.toBeInTheDocument();
  });

  it("renders explicit offline placeholders", () => {
    render(<DashboardScreen state={{ ...DASHBOARD_FIXTURE, connection: "offline", account: { ...DASHBOARD_FIXTURE.account, balance: null } }} />);
    expect(screen.getByText("Backend offline")).toBeInTheDocument();
    expect(screen.getAllByText("—").length).toBeGreaterThan(0);
  });
});

it("labels each dashboard sector with an AGENT badge", () => {
  render(<DashboardScreen state={DASHBOARD_FIXTURE} />);
  expect(screen.getAllByText("AGENT")).toHaveLength(8);
  for (const title of ["Market", "Open Positions", "Signals", "Risk Controls", "Recent Activity", "الأداء", "موجز السوق", "المساعد الذكي"]) {
    const heading = screen.getByText(title);
    expect(heading.closest("section,div")?.textContent).toContain("AGENT");
  }
});

