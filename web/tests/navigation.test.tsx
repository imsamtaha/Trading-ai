import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MobileNav } from "../components/layout/mobile-nav";
import { Sidebar } from "../components/layout/sidebar";
import { NAV_ITEMS } from "../lib/navigation";

describe("responsive navigation", () => {
  it("renders every destination with the active page announced", () => {
    render(
      <>
        <Sidebar active="dashboard" />
        <MobileNav active="dashboard" />
      </>,
    );

    for (const item of NAV_ITEMS) {
      expect(screen.getAllByText(item.label).length).toBeGreaterThan(0);
    }
    expect(screen.getByTestId("desktop-sidebar")).toBeInTheDocument();
    expect(screen.getByTestId("mobile-nav")).toBeInTheDocument();
    expect(
      screen.getAllByRole("link", { name: "Dashboard" })[0],
    ).toHaveAttribute("aria-current", "page");
  });
});
