import { atlasFetch } from "./client";
import { apiPath } from "./config";
import { mapPrivateDashboardState } from "./mappers";
import type { DashboardViewModel } from "./types";
export async function getDashboardState(signal?: AbortSignal, timeoutMs?: number): Promise<DashboardViewModel> {
  return mapPrivateDashboardState(await atlasFetch<unknown>(apiPath("/api/user/dashboard"), { cache: "no-store", credentials: "same-origin", signal }, timeoutMs));
}
