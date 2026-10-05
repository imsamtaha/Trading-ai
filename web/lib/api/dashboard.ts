import { requestJson } from "./client";
import { mapDashboardState, mapPositions } from "./mappers";
import type { DashboardViewModel, Position } from "./types";
export async function getDashboardState(): Promise<DashboardViewModel> { return mapDashboardState(await requestJson<unknown>("/dashboard/mt5-state")); }
export async function getPositions(): Promise<Position[]> { return mapPositions(await requestJson<unknown>("/mt5/positions")); }
