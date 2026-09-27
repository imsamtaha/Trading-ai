import { atlasFetch } from "./client";
import { mapDashboardState, mapPositions } from "./mappers";
import type { DashboardViewModel, Position } from "./types";

export async function getDashboardState(): Promise<DashboardViewModel> {
  return mapDashboardState(await atlasFetch<unknown>("/dashboard/mt5-state"));
}

export async function getPositions(): Promise<Position[]> {
  const raw = await atlasFetch<Record<string, unknown>>("/mt5/positions");
  return mapPositions(raw.positions);
}
