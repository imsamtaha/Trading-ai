import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { RiskPanel } from "../features/risk/risk-panel";
import { mapDashboardState } from "../lib/api/mappers";

describe("RiskPanel", () => {
  it("renders only risk values supplied by the backend", () => {
    const risk = mapDashboardState({ risk: { level: "MEDIUM", daily_loss_usage: 12, drawdown_percent: 3, exposure_percent: 18, aggregate_open_risk: 45, warnings: ["Limit approaching"], protection_state: "ACTIVE" } }).risk;
    render(<RiskPanel risk={risk} />);
    expect(screen.getByText("MEDIUM")).toBeInTheDocument();
    expect(screen.getByText("Limit approaching")).toBeInTheDocument();
    expect(screen.getByText(/Protection: ACTIVE/)).toBeInTheDocument();
  });
  it("makes unavailable risk explicit", () => {
    render(<RiskPanel risk={null} />);
    expect(screen.getByText(/Risk telemetry unavailable/i)).toBeInTheDocument();
  });
});
