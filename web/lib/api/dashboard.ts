import { atlasFetch } from "./client";
import { apiPath } from "./config";
import { mapDashboardState } from "./mappers";
import type { DashboardViewModel } from "./types";
export async function getDashboardState(signal?: AbortSignal, timeoutMs?: number): Promise<DashboardViewModel> {
  return mapDashboardState(await atlasFetch<unknown>(apiPath("/dashboard/atlas"), { cache: "no-store", signal }, timeoutMs));
}
