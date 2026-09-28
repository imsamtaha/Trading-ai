import type { ReactElement } from "react";
import { AtlasAppShell } from "../../components/layout/atlas-shell";
import { MarketWorkspace } from "../../features/markets/market-workspace";
export default function MarketsPage(): ReactElement { return <AtlasAppShell><MarketWorkspace /></AtlasAppShell>; }
