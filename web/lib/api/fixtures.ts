import type { BackendDashboardDto } from "./types";
/** Minimal offline fixture for deterministic UI development; contains no account secrets or fabricated balances. */
export const offlineDashboardFixture: BackendDashboardDto = { status: "OFFLINE", mode: "READ_ONLY", account: null, positions: [], risk: null };
