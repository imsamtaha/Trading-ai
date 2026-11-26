import { describe, expect, it, vi } from "vitest";
import AtlasPage from "@/app/page";

const { redirect } = vi.hoisted(() => ({ redirect: vi.fn() }));
vi.mock("next/navigation", async (importOriginal) => ({
  ...await importOriginal<typeof import("next/navigation")>(),
  redirect,
}));

describe("ATLAS service entry", () => {
  it("opens sign-in without a dashboard", () => {
    AtlasPage();
    expect(redirect).toHaveBeenCalledWith("/login");
  });
});
