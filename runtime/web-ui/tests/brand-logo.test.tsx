import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AtlasWordmark } from "@/components/brand/atlas-wordmark";
import LoginPage from "@/app/login/page";
import { AtlasShell } from "@/components/layout/atlas-shell";

describe("ATLAS brand logo", () => {
  it("shows the JUST AI Intelligence logo in navigation", () => {
    render(<AtlasWordmark />);
    expect(screen.getByRole("img", { name: "JUST AI Intelligence" })).toHaveAttribute("src", "/just-ai-intelligence.webp");
  });
  it("uses the same logo on sign-in", () => {
    render(<LoginPage />);
    expect(screen.getByRole("img", { name: "JUST AI Intelligence" })).toHaveAttribute("src", "/just-ai-intelligence.webp");
  });
  it("keeps the logo visible in the mobile app header", () => {
    render(<AtlasShell>workspace</AtlasShell>);
    expect(screen.getAllByRole("img", { name: "JUST AI Intelligence" })).toHaveLength(2);
  });
});
