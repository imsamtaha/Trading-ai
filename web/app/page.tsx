"use client";
import { useEffect, useState } from "react";
import type { ReactElement } from "react";
import { AtlasAppShell } from "../components/layout/atlas-shell";
import { DashboardScreen } from "../features/dashboard/dashboard-screen";
import { getDashboardState } from "../lib/api/dashboard";
import { mapDashboardState } from "../lib/api/mappers";
import type { DashboardViewModel } from "../lib/api/types";
export { AtlasAppShell };

export default function Home(): ReactElement {
  const [state, setState] = useState<DashboardViewModel>(() => mapDashboardState({ status: "OFFLINE" }));
  useEffect(() => { let active = true; getDashboardState().then(value => { if (active) setState(value); }).catch(() => { if (active) setState(mapDashboardState({ status: "OFFLINE" })); }); return () => { active = false; }; }, []);
  return <AtlasAppShell><DashboardScreen state={state} /></AtlasAppShell>;
}
