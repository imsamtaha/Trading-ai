import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PositionsPanel } from "../features/trades/positions-panel";
import { mapPosition } from "../lib/api/mappers";
describe("PositionsPanel", () => {
  it("renders supplied position details", () => { render(<PositionsPanel positions={[mapPosition({ symbol: "EURUSD", direction: "BUY", volume: 0.2, price_open: 1.1, sl: 1.09, tp: 1.12, profit: 20 })]} />); expect(screen.getByText("EURUSD")).toBeInTheDocument(); expect(screen.getByText("BUY")).toBeInTheDocument(); expect(screen.getByText("1.1")).toBeInTheDocument(); });
  it("distinguishes empty and unavailable states", () => { const { rerender } = render(<PositionsPanel positions={[]} />); expect(screen.getByText(/No open positions/i)).toBeInTheDocument(); rerender(<PositionsPanel positions={null} />); expect(screen.getByText(/Positions are unavailable/i)).toBeInTheDocument(); });
});
