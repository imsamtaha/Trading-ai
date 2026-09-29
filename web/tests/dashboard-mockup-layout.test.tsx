import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DashboardScreen } from "@/features/dashboard/dashboard-screen";
import { DASHBOARD_FIXTURE } from "@/lib/api/fixtures";

describe("ATLAS mockup dashboard layout", () => {
  it("renders concise mockup sections and four primary actions", () => {
    render(<DashboardScreen state={DASHBOARD_FIXTURE} language="en" />);
    expect(screen.getByTestId("atlas-dashboard-topbar")).toBeInTheDocument();
    expect(screen.getByTestId("atlas-insight-grid")).toBeInTheDocument();
    expect(screen.getByTestId("atlas-stat-strip")).toBeInTheDocument();
    for (const label of ["Trend", "Signal", "Bias", "Conf", "Balance", "Equity", "P/L", "Pos", "Engine"]) {
      expect(screen.getAllByText(label).length).toBeGreaterThan(0);
    }
    const nav = screen.getByRole("navigation", { name: "Dashboard actions" });
    expect(nav.querySelectorAll("a")).toHaveLength(4);
    for (const label of ["Home", "Markets", "Trade", "ATLAS AI"]) {
      expect(screen.getByRole("link", { name: label })).toBeInTheDocument();
    }
  });
});