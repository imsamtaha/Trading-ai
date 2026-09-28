import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MarketWorkspace } from "../features/markets/market-workspace";
describe("MarketWorkspace", () => {
  it("shows a stable empty chart state", () => { render(<MarketWorkspace />); expect(screen.getByText(/Market data is unavailable/i)).toBeInTheDocument(); });
});
