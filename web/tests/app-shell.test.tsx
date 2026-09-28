import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AtlasAppShell } from "../app/page";

describe("ATLAS app shell", () => {
  it("renders the ATLAS trading workspace identity", () => {
    render(<AtlasAppShell />);

    expect(screen.getAllByText("ATLAS").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Trading Intelligence").length).toBeGreaterThan(0);
    expect(screen.getByTestId("atlas-app-shell")).toBeInTheDocument();
  });
});
