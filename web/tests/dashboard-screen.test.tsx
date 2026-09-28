import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DashboardScreen } from "../features/dashboard/dashboard-screen";
import { mapDashboardState } from "../lib/api/mappers";

describe("DashboardScreen", () => {
  it("renders account mode, metrics, markets, and risk status", () => {
    render(<DashboardScreen state={mapDashboardState({ status: "ONLINE", mode: "READ_ONLY", account: { balance: 1000, equity: 990, currency: "USD", floating_profit: -10 }, floating_position_pnl: -10, risk: { level: "LOW" }, financial_market: { market_board: [{ label: "Gold", price: 2300, change_percent: 0.5, market_state: "OPEN" }] } })} />);
    expect(screen.getByText("READ_ONLY")).toBeInTheDocument();
    expect(screen.getByText("$1,000.00")).toBeInTheDocument();
    expect(screen.getByText("$990.00")).toBeInTheDocument();
    expect(screen.getByText("-$10.00")).toBeInTheDocument();
    expect(screen.getByText("LOW")).toBeInTheDocument();
    expect(screen.getByText("Gold")).toBeInTheDocument();
  });
  it("shows explicit offline and unknown value placeholders", () => {
    render(<DashboardScreen state={mapDashboardState({ status: "OFFLINE" })} />);
    expect(screen.getByText(/Backend is offline/i)).toBeInTheDocument();
    expect(screen.getAllByText("—").length).toBeGreaterThan(2);
  });
});
