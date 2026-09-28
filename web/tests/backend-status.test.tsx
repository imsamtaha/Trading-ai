import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { BackendStatus, resolveBackendStatus } from "../components/system/backend-status";
describe("BackendStatus", () => {
  it("never reports connectivity without a successful health and account read", () => { expect(resolveBackendStatus(false, true)).toBe("offline"); expect(resolveBackendStatus(true, false)).toBe("degraded"); expect(resolveBackendStatus(true, true)).toBe("online"); });
  it.each([["checking", "Checking backend"], ["online", "Backend online"], ["offline", "Backend offline"], ["degraded", "Backend degraded"]] as const)("labels %s correctly", (status, label) => { render(<BackendStatus status={status} />); expect(screen.getByText(label)).toBeInTheDocument(); });
});
