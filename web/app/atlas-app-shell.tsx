import { AtlasShell } from "@/components/layout/atlas-shell";

export function AtlasAppShell() {
  return (
    <AtlasShell>
      <section data-testid="atlas-app-shell" className="atlas-dashboard-hero" id="dashboard">
        <p className="eyebrow">JUST AI</p>
        <h1 className="atlas-hero-title">Trading cockpit</h1>
        <p className="atlas-hero-copy">Real insights. Smarter decisions. Better trading discipline.</p>
      </section>
    </AtlasShell>
  );
}
