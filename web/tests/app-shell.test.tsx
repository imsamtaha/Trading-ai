import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import AtlasPage from "@/app/page";

describe("ATLAS app shell", () => {
  it("renders the ATLAS trading intelligence shell", () => {
    render(<AtlasPage />);
    expect(screen.getByTestId("atlas-app-shell")).toBeInTheDocument();
    expect(screen.getAllByText("ATLAS").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Trading Intelligence").length).toBeGreaterThan(0);
  });
});
