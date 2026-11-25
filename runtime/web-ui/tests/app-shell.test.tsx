import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import AtlasPage from "@/app/page";
import DashboardPage from "@/app/dashboard/page";

const { redirect } = vi.hoisted(() => ({ redirect: vi.fn() }));
vi.mock("next/navigation", async (importOriginal) => ({
  ...await importOriginal<typeof import("next/navigation")>(),
  redirect,
}));

describe("ATLAS dashboard entry points", () => {
  it("links to the dashboard and preserves the connection and subscription entry points", () => {
    render(<AtlasPage />);
    expect(screen.getByRole("link", { name: "Open the ATLAS dashboard" })).toHaveAttribute("href", "/dashboard");
    expect(screen.getByRole("link", { name: "Connection settings" })).toHaveAttribute("href", "/connect");
    expect(screen.getByRole("link", { name: "Subscription plans" })).toHaveAttribute("href", "/subscribe");
  });

  it("hands the old dashboard URL off to the private Sites dashboard", () => {
    DashboardPage();
    expect(redirect).toHaveBeenCalledWith("https://atlas-intelligence.imsamtaha-ai.chatgpt.site/");
  });
});
