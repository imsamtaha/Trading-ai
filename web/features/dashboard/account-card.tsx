import type { ReactElement } from "react";
import type { AccountViewModel } from "../../lib/api/types";
import { StatCard } from "./stat-card";
const money = (value: number | null, currency: string | null) => value === null ? "—" : new Intl.NumberFormat("en-US", { style: "currency", currency: currency ?? "USD", maximumFractionDigits: 2 }).format(value);
export function AccountCard({ account }: { account: AccountViewModel }): ReactElement {
  return <div className="atlas-metric-grid"><StatCard label="Balance" value={money(account.balance, account.currency)} /><StatCard label="Equity" value={money(account.equity, account.currency)} /><StatCard label="Floating P/L" value={money(account.floatingPnl, account.currency)} /></div>;
}
