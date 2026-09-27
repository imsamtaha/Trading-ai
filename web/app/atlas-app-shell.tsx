import { AtlasShell } from "@/components/layout/atlas-shell";
import { DashboardScreen } from "@/features/dashboard/dashboard-screen";
import { DASHBOARD_FIXTURE } from "@/lib/api/fixtures";

export function AtlasAppShell() {
  return (
    <AtlasShell>
      <section data-testid="atlas-app-shell">
        <DashboardScreen state={DASHBOARD_FIXTURE} />
      </section>
    </AtlasShell>
  );
}
