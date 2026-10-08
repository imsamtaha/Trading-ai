import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import LoginPage from "@/app/login/page";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
describe("ATLAS login", () => {
  it("offers Google and email sign-in with a status message", () => {
    render(<LoginPage />);
    expect(screen.getByText("Continue with Google")).toBeInTheDocument();
    expect(document.getElementById("googleLogin")).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Email" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Sign out" })).not.toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveAttribute("id", "account-status");
  });
  it("keeps sign-out hidden before authentication", () => {
    const style = document.createElement("style");
    style.textContent = readFileSync(resolve(process.cwd(), "app/globals.css"), "utf8");
    document.head.append(style);
    render(<LoginPage />);
    expect(screen.queryByRole("button", { name: "Sign out" })).not.toBeInTheDocument();
    style.remove();
  });
});
