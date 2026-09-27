import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import LoginPage from "@/app/login/page";
describe("ATLAS login", () => {
  it("preserves the existing Google auth script's controls and status IDs", () => {
    render(<LoginPage />);
    expect(screen.getByRole("button", { name: "Continue with Google" })).toHaveAttribute("id", "google-sign-in");
    expect(document.getElementById("google-sign-out")).toHaveAttribute("hidden");
    expect(screen.getByRole("status")).toHaveAttribute("id", "account-status");
  });
});
