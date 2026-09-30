import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { fireEvent } from "@testing-library/react";
import { MarketWorkspace } from "@/features/markets/market-workspace";

describe("MarketWorkspace", () => {
  it("renders symbol and timeframe controls", () => {
    render(<MarketWorkspace candles={[]} symbol="BTCUSDT" timeframe="1h" />);
    expect(screen.getByText("BTCUSDT")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "1h" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByText("Market data unavailable")).toBeInTheDocument();
  });
  it("changes symbols and timeframes through the parent callback", () => {
    const onChange = vi.fn();
    render(<MarketWorkspace candles={[]} symbol="XAUUSD" timeframe="1h" onChange={onChange} />);
    fireEvent.change(screen.getByLabelText("Instrument"), { target: { value: "EURUSD" } });
    fireEvent.click(screen.getByRole("button", { name: "15m" }));
    expect(onChange).toHaveBeenCalledWith("EURUSD", "1h");
    expect(onChange).toHaveBeenCalledWith("XAUUSD", "15m");
  });
});


describe("AI chart controls", () => {
  it("lets traders toggle common indicators", () => {
    render(<MarketWorkspace candles={[]} symbol="XAUUSD" timeframe="1h" />);
    expect(screen.getByRole("button", { name: "EMA 20" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "SMA 50" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "RSI 14" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "EMA 20" }));
    expect(screen.getByRole("button", { name: "EMA 20" })).toHaveAttribute("aria-pressed", "true");
  });
});
