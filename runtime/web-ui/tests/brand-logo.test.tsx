import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AtlasWordmark } from "@/components/brand/atlas-wordmark";
import LoginPage from "@/app/login/page";
import { AtlasShell } from "@/components/layout/atlas-shell";

describe("ATLAS brand logo", () => {
  it("shows the isolated A and ATLAS mark in navigation", () => {
    render(<AtlasWordmark />);
    expect(screen.getByRole("img", { name: "ATLAS" })).toHaveAttribute("src", "/atlas-logo.webp");
  });
  it("uses the same logo on sign-in", () => {
    render(<LoginPage />);
    expect(screen.getByRole("img", { name: "ATLAS" })).toHaveAttribute("src", "/atlas-logo.webp");
  });
  it("keeps the logo visible in the mobile app header", () => {
    render(<AtlasShell>workspace</AtlasShell>);
    expect(screen.getAllByRole("img", { name: "ATLAS" })).toHaveLength(2);
  });
});
