import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import DashboardPage from "@/app/dashboard/page";
import { AtlasApiError } from "@/lib/api/client";
import { getDashboardState } from "@/lib/api/dashboard";

vi.mock("@/lib/api/dashboard", () => ({ getDashboardState: vi.fn() }));
beforeEach(() => { localStorage.clear(); vi.resetAllMocks(); });

it("keeps the private account behind sign-in and remembers the workspace language", async () => {
  vi.mocked(getDashboardState).mockRejectedValue(new AtlasApiError("/api/user/dashboard", 401, "Sign in"));
  render(<DashboardPage />);
  expect(await screen.findByRole("link", { name: "سجّل الدخول لعرض حسابك" })).toHaveAttribute("href", "/login");
  fireEvent.click(screen.getByRole("button", { name: "English" }));
  expect(screen.getByRole("main")).toHaveAttribute("dir", "ltr");
  expect(localStorage.getItem("atlas-dashboard-language")).toBe("en");
  expect(screen.getByRole("link", { name: "Council training" })).toHaveAttribute("href", "https://atlas-tiger-shield-command-center.imsamtaha-ai.chatgpt.site/#training");
  expect(screen.queryByText("Open Positions")).toBeNull();
});

it("allows a failed account request to be retried", async () => {
  localStorage.setItem("atlas-dashboard-language", "en");
  vi.mocked(getDashboardState).mockRejectedValueOnce(new Error("Offline"))
    .mockRejectedValueOnce(new AtlasApiError("/api/user/dashboard", 401, "Sign in"));
  render(<DashboardPage />);
  fireEvent.click(await screen.findByRole("button", { name: "Retry" }));
  expect(await screen.findByRole("link", { name: "Sign in to view your account" })).toBeInTheDocument();
  expect(getDashboardState).toHaveBeenCalledTimes(2);
});
