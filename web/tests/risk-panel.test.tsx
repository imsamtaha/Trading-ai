import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { RiskPanel } from "@/features/risk/risk-panel";
import { DASHBOARD_FIXTURE } from "@/lib/api/fixtures";

describe("RiskPanel", () => {
  it("renders backend-provided risk values", () => {
    render(<RiskPanel risk={DASHBOARD_FIXTURE.risk} />);
    expect(screen.getByText("Risk Controls")).toBeInTheDocument();
    expect(screen.getAllByText("28%").length).toBeGreaterThan(0);
    expect(screen.getByText("Protected")).toBeInTheDocument();
  });
});
