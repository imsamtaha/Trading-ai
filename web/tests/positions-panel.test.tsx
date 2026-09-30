import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PositionsPanel } from "@/features/trades/positions-panel";

const position = { symbol: "BTCUSDT", direction: "LONG", size: .5, entry: 66420, current: 67432, pnl: 506, stopLoss: 65500, takeProfit: 69000, status: "OPEN" };

describe("PositionsPanel", () => {
  it("renders open positions", () => {
    render(<PositionsPanel positions={[position]} available />);
    expect(screen.getByText("BTCUSDT")).toBeInTheDocument();
    expect(screen.getByText("LONG")).toBeInTheDocument();
    expect(screen.getByText("0.5")).toBeInTheDocument();
    expect(screen.getByText("OPEN")).toBeInTheDocument();
  });
  it("renders empty and unavailable states", () => {
    const { rerender } = render(<PositionsPanel positions={[]} available />);
    expect(screen.getByText("No open positions")).toBeInTheDocument();
    rerender(<PositionsPanel positions={[]} available={false} />);
    expect(screen.getByText("Positions unavailable")).toBeInTheDocument();
  });
});
