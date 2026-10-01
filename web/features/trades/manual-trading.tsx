"use client";
import { useEffect, useState } from "react";
import { atlasFetch } from "@/lib/api/client";
import { apiPath } from "@/lib/api/config";

type TradingState = { connected: boolean; active: boolean; account_type: "DEMO" | "REAL" | null; account_masked?: string; server_enabled?: boolean };
const path = (route: string) => apiPath(`/api/mt5-demo/${route}`);

export function ManualTrading({ language = "en" }: { language?: "ar" | "en" }) {
  const ar = language === "ar";
  const [state, setState] = useState<TradingState | null>(null);
  const [symbol, setSymbol] = useState("");
  const [direction, setDirection] = useState<"BUY" | "SELL">("BUY");
  const [volume, setVolume] = useState("");
  const [stopLoss, setStopLoss] = useState("");
  const [takeProfit, setTakeProfit] = useState("");
  const [reviewing, setReviewing] = useState(false);
  const [requestId, setRequestId] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  useEffect(() => {
    let mounted = true;
    atlasFetch<TradingState>(path("trading-state"), { credentials: "same-origin", cache: "no-store" })
      .then((value) => { if (mounted) setState(value); })
      .catch(() => { if (mounted) setMessage("Trading state unavailable."); });
    return () => { mounted = false; };
  }, []);
  if (!state?.connected) return <section id="trade" className="atlas-card atlas-manual-trading atlas-feature-3d" dir={ar ? "rtl" : "ltr"} lang={language}><h2>{ar ? "تداول MT5" : "MT5 trading"}</h2><p role={message ? "status" : undefined}>{message || "Connect MT5 to open the trading workspace."}</p></section>
  const mode = state.account_type === "REAL" ? "Live" : "Demo";
  async function activate() {
    if (!state || state.account_type !== "REAL") return;
    setBusy(true); setMessage("");
    try {
      const next = await atlasFetch<TradingState>(path("activate-trading"), {
        method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ account_type: "REAL", confirmed: true }),
      });
      setState(next);
    } catch { setMessage("Unable to activate Live trading. Check the account and server setting."); }
    finally { setBusy(false); }
  }
  async function submitOrder() {
    if (!state?.active || !state.account_type || !reviewing) return;
    setBusy(true); setMessage("");
    try {
      const result = await atlasFetch<{ status: string; ticket?: number }>(path("order"), {
        method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ request_id: requestId, account_type: state.account_type, symbol, direction,
          volume: Number(volume), stop_loss: Number(stopLoss), take_profit: Number(takeProfit), confirmed: true }),
      });
      setMessage(result.status === "FILLED" ? `Order filled, ticket ${result.ticket}.` : "Broker did not confirm a fill.");
    } catch { setMessage("Order not confirmed. Check your MT5 account and order history before trying again."); }
    finally { setReviewing(false); setBusy(false); }
  }
  return <section id="trade" className="atlas-card atlas-manual-trading atlas-feature-3d" dir={ar ? "rtl" : "ltr"} lang={language}>
    <header className="atlas-trade-header"><h2>{ar ? "تداول MT5" : "MT5 trading"}</h2>
    <p className="atlas-trade-account">{`${ar ? (state.account_type === "REAL" ? "حقيقي" : "تجريبي") : `${mode} account`} ${state.account_masked ?? ""} · ${state.active ? (ar ? "جاهز" : "Ready") : (ar ? "غير مفعّل" : "Inactive")}`}</p></header>
    {!state.server_enabled && <p>{ar ? "إرسال الأوامر غير مفعّل" : "Order submission disabled."}</p>}
    {state.account_type === "REAL" && !state.active && state.server_enabled &&
      <button type="button" onClick={() => void activate()} disabled={busy}>{ar ? "تفعيل التداول الحقيقي" : "Activate Live trading"}</button>}
    {state.active && <>
      <form onSubmit={(event) => { event.preventDefault(); setRequestId(crypto.randomUUID()); setReviewing(true); setMessage(""); }}>
        <label className="atlas-trade-symbol">{ar ? "الرمز" : "Symbol"}<input required aria-label={ar ? "الرمز" : "Symbol"} dir="ltr" placeholder="EURUSD" value={symbol} onChange={(e) => { setSymbol(e.target.value); setReviewing(false); }} /></label>
        <label>{ar ? "الاتجاه" : "Side"}<select aria-label={ar ? "الاتجاه" : "Side"} value={direction} onChange={(e) => { setDirection(e.target.value as "BUY" | "SELL"); setReviewing(false); }}><option value="BUY">{ar ? "شراء" : "BUY"}</option><option value="SELL">{ar ? "بيع" : "SELL"}</option></select></label>
        <label>{ar ? "الحجم (لوت)" : "Volume"}<input required aria-label={ar ? "الحجم (لوت)" : "Volume"} dir="ltr" type="number" min="0.01" max="1" step="0.01" value={volume} onChange={(e) => { setVolume(e.target.value); setReviewing(false); }} /></label>
        <label>{ar ? "وقف الخسارة" : "Stop loss"}<input required aria-label={ar ? "وقف الخسارة" : "Stop loss"} dir="ltr" type="number" step="any" min="0.00001" value={stopLoss} onChange={(e) => { setStopLoss(e.target.value); setReviewing(false); }} /></label>
        <label>{ar ? "جني الربح" : "Take profit"}<input required aria-label={ar ? "جني الربح" : "Take profit"} dir="ltr" type="number" step="any" min="0.00001" value={takeProfit} onChange={(e) => { setTakeProfit(e.target.value); setReviewing(false); }} /></label>
        <button className="atlas-primary-button atlas-trade-review" type="submit" disabled={busy}>{ar ? "مراجعة الصفقة" : "Review order"}</button>
      </form>
      {reviewing && <div className="atlas-trade-confirmation" role="group" aria-label={ar ? "تأكيد الصفقة" : "Order confirmation"}>
        <p>{ar ? "تأكيد" : "Confirm"} {direction} {volume} {symbol} · {ar ? (state.account_type === "REAL" ? "حقيقي" : "تجريبي") : mode} {state.account_masked} · SL {stopLoss} · TP {takeProfit}</p>
        <button type="button" disabled={busy} onClick={() => void submitOrder()}>{ar ? "تأكيد الصفقة" : `Confirm ${mode} order`}</button>
        <button type="button" onClick={() => setReviewing(false)}>{ar ? "إلغاء" : "Cancel"}</button>
      </div>}
    </>}
    {message && <p role="status">{message}</p>}
  </section>;
}
