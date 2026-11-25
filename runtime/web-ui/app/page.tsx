import Link from "next/link";
import { AtlasShell } from "@/components/layout/atlas-shell";

export default function AtlasPage() {
  return (
    <AtlasShell>
      <main className="atlas-connect-page">
        <h1>ATLAS Intelligence</h1>
        <p><Link href="/dashboard">Open the ATLAS dashboard</Link></p>
        <p><Link href="/connect">Connection settings</Link> · <Link href="/subscribe">Subscription plans</Link></p>
      </main>
    </AtlasShell>
  );
}
