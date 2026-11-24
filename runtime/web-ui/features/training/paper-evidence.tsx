"use client";

import { useState } from "react";
import styles from "./training-panel.module.css";

export type PaperTrade = { id: string; symbol: string; status: "OPEN" | "CLOSED"; opened_at: string; closed_at: string | null; result_r: number | null };
export type TrainingSession = { date_utc: string; settled_examples: number };
export type ShadowReview = { status: string; generated_at: string | null; samples: number | null };

const PAGE_SIZE = 50;

export function PaperEvidence({ trades = [], sessions = [], review, language }: {
  trades?: PaperTrade[]; sessions?: TrainingSession[]; review?: ShadowReview | null; language: "ar" | "en";
}) {
  const ar = language === "ar";
  const [page, setPage] = useState(0);
  const [query, setQuery] = useState("");
  const filtered = trades.filter((trade) => trade.symbol.toLowerCase().includes(query.trim().toLowerCase()));
  const pages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const current = Math.min(page, pages - 1);
  const values = filtered.slice(current * PAGE_SIZE, (current + 1) * PAGE_SIZE);
  const formatDate = (date: string | null) => date ? new Date(date).toLocaleString(ar ? "ar-LB" : "en-GB", { timeZone: "Asia/Beirut" }) : "—";
  return <>
    <h3>{ar ? "مراجعة scikit-learn" : "scikit-learn Shadow Review"}</h3>
    <p>{review ? <><b>{review.status}</b> · {review.samples ?? "—"} {ar ? "عينة" : "samples"} · {formatDate(review.generated_at)}</>
      : ar ? "تقرير تقييم موثّق غير متاح." : "No attested evaluation report is available."}</p>
    <h3>{ar ? "جلسات تدريب المجلس" : "Council training sessions"}</h3>
    {sessions.length ? <div className={styles.scroll}><table>
      <caption>{ar ? "نتائج ورقية مسوّاة حسب تاريخ UTC" : "Settled PAPER examples by UTC date"}</caption>
      <thead><tr><th scope="col">{ar ? "التاريخ" : "Date"}</th><th scope="col">{ar ? "أمثلة مسوّاة" : "Settled examples"}</th></tr></thead>
      <tbody>{sessions.map((session) => <tr key={session.date_utc}><td>{session.date_utc}</td><td>{session.settled_examples}</td></tr>)}</tbody>
    </table></div> : <p>{ar ? "لا توجد جلسات متاحة." : "No sessions are available."}</p>}
    <h3>{ar ? "سجل التداول الورقي" : "PAPER trade history"}</h3>
    <label className={styles.search}>{ar ? "تصفية حسب الرمز" : "Filter by symbol"}
      <input type="search" value={query} onChange={(event) => { setQuery(event.target.value); setPage(0); }} />
    </label>
    {values.length ? <div className={styles.scroll}><table>
      <thead><tr>{(ar ? ["الرمز","الحالة","الدخول","الخروج","R"] : ["Symbol","Status","Opened","Closed","R"]).map((label) => <th key={label} scope="col">{label}</th>)}</tr></thead>
      <tbody>{values.map((trade) => <tr key={trade.id}><th scope="row"><bdi>{trade.symbol}</bdi></th><td>{trade.status}</td><td>{formatDate(trade.opened_at)}</td><td>{formatDate(trade.closed_at)}</td><td>{trade.result_r ?? "—"}</td></tr>)}</tbody>
    </table></div> : <p>{ar ? "لا توجد سجلات مطابقة." : "No matching records are available."}</p>}
    {pages > 1 && <div className={styles.pager}>
      <button type="button" disabled={current === 0} onClick={() => setPage(current - 1)}>{ar ? "السابق" : "Previous"}</button>
      <span>{current + 1} / {pages}</span>
      <button type="button" disabled={current === pages - 1} onClick={() => setPage(current + 1)}>{ar ? "التالي" : "Next"}</button>
    </div>}
  </>;
}
