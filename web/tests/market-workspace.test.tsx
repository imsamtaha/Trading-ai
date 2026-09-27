import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MarketWorkspace } from "@/features/markets/market-workspace";

describe("MarketWorkspace", () => {
  it("renders symbol and timeframe controls", () => {
    render(<MarketWorkspace candles={[]} symbol="BTCUSDT" timeframe="1h" />);
    expect(screen.getByText("BTCUSDT")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "1h" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByText("Market data unavailable")).toBeInTheDocument();
  });
});
