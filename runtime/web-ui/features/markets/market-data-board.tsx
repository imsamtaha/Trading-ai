"use client";

import { useState } from "react";
import type { MarketBriefing } from "@/lib/api/briefing";

const translations: Record<string, string> = {
  "US Equities": "الأسهم الأميركية", Volatility: "التقلب", Commodities: "السلع",
  FX: "العملات", "Digital Assets": "الأصول الرقمية", FRESH: "حديث",
  DELAYED: "متأخر", STALE: "قديم", UNKNOWN: "الوقت غير معروف", UNAVAILABLE: "غير متاح",
};

export function MarketDataBoard({ briefing, language }: { briefing: MarketBriefing | null; language: "ar" | "en" }) {
  const [category, setCategory] = useState("");
  const ar = language === "ar";
  const text = (value: string) => ar ? translations[value] ?? value : value;
  const quotes = briefing?.quotes ?? [];
  const categories = [...new Set(quotes.map((quote) => quote.category))];
  const activeCategory = categories.includes(category) ? category : "";
  const visible = quotes.filter((quote) => !activeCategory || quote.category === activeCategory);
  const available = quotes.filter((quote) => quote.price !== null);
  const fresh = available.filter((quote) => quote.freshness === "FRESH");
  const rising = fresh.filter((quote) => quote.changePct !== null && quote.changePct > 0).length;
  const falling = fresh.filter((quote) => quote.changePct !== null && quote.changePct < 0).length;
  const price = new Intl.NumberFormat(ar ? "ar-LB" : "en-US", { maximumFractionDigits: 6 });
  const time = new Intl.DateTimeFormat(ar ? "ar-LB" : "en-GB", {
    month: "short", day: "numeric", hour: "2-digit", minute: "2-digit", timeZone: "Asia/Beirut",
  });
  return <section id="markets" className="atlas-card atlas-data-board" aria-label={ar ? "لوحة بيانات الأسواق" : "Market data board"}>
    <header>
      <div>
        <h2>{ar ? "لوحة بيانات الأسواق" : "Market Data Board"}</h2>
        <p>{ar ? "الأسعار العامة ومقارنتها بإغلاق الجلسة السابقة. أوقات الأسعار بتوقيت بيروت." : "Public quotes and changes from the previous session close. Quote times are shown in Beirut time."}</p>
      </div>
      <label>{ar ? "الفئة" : "Asset class"} <select value={activeCategory} onChange={(event) => setCategory(event.target.value)}>
        <option value="">{ar ? "الكل" : "All markets"}</option>
        {categories.map((name) => <option value={name} key={name}>{text(name)}</option>)}
      </select></label>
    </header>
    {briefing?.asOf && <p className="atlas-data-asof">{ar ? "آخر جلب" : "Last fetched"} · <time dateTime={briefing.asOf}>{time.format(new Date(briefing.asOf))}</time></p>}
    {!quotes.length ? <p role="status">{ar ? "بيانات الأسواق غير متاحة حالياً." : "Market data is currently unavailable."}</p> : <>
      <dl className="atlas-data-summary">
        <div><dt>{ar ? "أسعار متاحة" : "Quotes available"}</dt><dd>{available.length}/{quotes.length}</dd></div>
        <div><dt>{ar ? "أسعار حديثة" : "Fresh quotes"}</dt><dd>{fresh.length}</dd></div>
        <div><dt>{ar ? "صعود / هبوط حديث" : "Fresh gainers / decliners"}</dt><dd>{fresh.length ? <bdi>{rising} / {falling}</bdi> : "—"}</dd></div>
      </dl>
      <div className="atlas-data-scroll" role="region" tabIndex={0} aria-label={ar ? "جدول الأسعار" : "Quote table"}>
        <table>
          <thead><tr><th scope="col">{ar ? "الأداة" : "Instrument"}</th><th scope="col">{ar ? "السعر" : "Price"}</th><th scope="col">{ar ? "تغيّر الجلسة" : "Session change"}</th><th scope="col">{ar ? "الحالة والمصدر" : "Status and source"}</th></tr></thead>
          <tbody>{visible.map((quote) => <tr key={quote.symbol}>
            <th scope="row">{quote.label}<small><bdi>{quote.symbol}</bdi> · {text(quote.category)}</small></th>
            <td>{quote.price === null ? "—" : <bdi>{price.format(quote.price)}</bdi>}</td>
            <td data-tone={quote.changePct === null || quote.changePct === 0 ? undefined : quote.changePct > 0 ? "up" : "down"}>{quote.changePct === null ? "—" : <bdi>{quote.changePct > 0 ? "+" : ""}{quote.changePct.toFixed(2)}%</bdi>}</td>
            <td><span className="atlas-quote-state" data-state={quote.freshness}>{text(quote.freshness)}</span>
              {(quote.provider || quote.quoteTime) && <small>{quote.provider}{quote.provider && quote.quoteTime ? " · " : ""}{quote.quoteTime && <time dateTime={quote.quoteTime}>{time.format(new Date(quote.quoteTime))}</time>}</small>}
            </td>
          </tr>)}</tbody>
        </table>
      </div>
    </>}
  </section>;
}
