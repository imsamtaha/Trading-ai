import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AtlasShell } from "@/components/layout/atlas-shell";

const labels = ["Dashboard", "Markets", "Trade", "Signals", "Risk", "Analytics", "News", "ATLAS AI", "Account"];

describe("ATLAS navigation", () => {
  it("renders desktop and mobile destinations with dashboard active", () => {
    render(<AtlasShell><div>content</div></AtlasShell>);
    expect(screen.getByTestId("desktop-sidebar")).toBeInTheDocument();
    expect(screen.getByTestId("mobile-nav")).toBeInTheDocument();
    for (const label of labels) expect(screen.getAllByText(label).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("link", { name: "Dashboard" })[0]).toHaveAttribute("aria-current", "page");
    expect(screen.getAllByRole("link", { name: "Account" })[0]).toHaveAttribute("href", "/login");
  });
});
