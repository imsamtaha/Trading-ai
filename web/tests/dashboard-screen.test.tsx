import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DashboardScreen } from "@/features/dashboard/dashboard-screen";
import { DASHBOARD_FIXTURE } from "@/lib/api/fixtures";

describe("DashboardScreen", () => {
  it("renders account and market telemetry", () => {
    render(<DashboardScreen state={DASHBOARD_FIXTURE} />);
    expect(screen.getByText("10,000.00")).toBeInTheDocument();
    expect(screen.getByText("10,248.42")).toBeInTheDocument();
    expect(screen.getByText("EURUSD")).toBeInTheDocument();
    expect(screen.getByText("XAUUSD")).toBeInTheDocument();
  });

  it("renders explicit offline placeholders", () => {
    render(<DashboardScreen state={{ ...DASHBOARD_FIXTURE, connection: "offline", account: { ...DASHBOARD_FIXTURE.account, balance: null } }} />);
    expect(screen.getByText("Backend offline")).toBeInTheDocument();
    expect(screen.getByText("—")).toBeInTheDocument();
  });
});
