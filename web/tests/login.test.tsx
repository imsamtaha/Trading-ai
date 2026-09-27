import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import LoginPage from "@/app/login/page";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
describe("ATLAS login", () => {
  it("preserves the existing Google auth script's controls and status IDs", () => {
    render(<LoginPage />);
    expect(screen.getByRole("button", { name: "Continue with Google" })).toHaveAttribute("id", "google-sign-in");
    expect(document.getElementById("google-sign-out")).toHaveAttribute("hidden");
    expect(screen.getByRole("status")).toHaveAttribute("id", "account-status");
  });
  it("keeps sign-out hidden before authentication", () => {
    const style = document.createElement("style");
    style.textContent = readFileSync(resolve(process.cwd(), "app/globals.css"), "utf8");
    document.head.append(style);
    render(<LoginPage />);
    expect(getComputedStyle(document.getElementById("google-sign-out")!).display).toBe("none");
    style.remove();
  });
});
