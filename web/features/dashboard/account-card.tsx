import type { AccountViewModel, ConnectionState } from "@/lib/api/types";

const money = (v: number | null) => v == null ? "—" : v.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export function AccountCard({ account, connection }: { account: AccountViewModel; connection: ConnectionState }) {
  return (
    <article className="atlas-card atlas-account-card" id="account">
      <div><span className="atlas-card-label">FxPro / MT5</span><strong>{account.mode ?? "Unknown mode"}</strong></div>
      <div className={`atlas-connection atlas-connection--${connection}`}>{connection === "connected" ? "Connected" : connection === "offline" ? "Backend offline" : "Connection unknown"}</div>
      <div className="atlas-account-balance"><span>Balance</span><strong>{money(account.balance)}</strong><small>USD</small></div>
    </article>
  );
}
