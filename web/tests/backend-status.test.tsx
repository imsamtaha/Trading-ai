import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { BackendStatus } from "@/components/system/backend-status";
describe("BackendStatus", () => {
  for (const [status, label] of [["checking","Checking backend"],["online","Backend online"],["offline","Backend offline"],["degraded","Backend degraded"]] as const) {
    it(`renders ${status} accurately`, () => {
      render(<BackendStatus status={status} />);
      expect(screen.getByRole("status")).toHaveTextContent(label);
    });
  }
});
