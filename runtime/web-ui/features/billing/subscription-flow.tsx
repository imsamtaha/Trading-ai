"use client";
import { useEffect, useState } from "react";
import { atlasFetch } from "@/lib/api/client";
import { apiPath } from "@/lib/api/config";
type Plan = { id: string; name: string; monthly_price: number; features: string[] };
const arabicFeature: Record<string, string> = {
  "Everything in Free": "كل ميزات الحساب الأساسي",
  "Verified real-account connection (read-only)": "ربط حساب MT5 الحقيقي للمتابعة فقط بعد تأكيد الدفع",
  "Alerts": "تنبيهات", "Extended analytics": "تحليلات موسّعة",
  "Everything in Starter": "كل ميزات Starter", "Deeper analytics": "تحليلات أعمق",
  "Longer activity history": "سجل صفقات أطول", "Priority support": "دعم ذو أولوية",
  "Everything in Pro": "كل ميزات Pro", "Advanced monitoring": "مراقبة متقدمة",
  "Expanded history": "سجل موسّع", "Premium support": "دعم مميز",
};
export function SubscriptionFlow() {
  const [language, setLanguage] = useState<"ar" | "en">("ar");
  const [email, setEmail] = useState<string | null>(null);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [status, setStatus] = useState("");
  const [payment, setPayment] = useState<{ reference: string; recipient?: string; phone?: string; support?: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const ar = language === "ar";
  useEffect(() => {
    let active = true;
    Promise.all([
      atlasFetch<{ user: { email: string } }>(apiPath("/api/me"), { credentials: "same-origin" }),
      atlasFetch<{ plans: Plan[] }>(apiPath("/billing/plans")),
    ]).then(([me, catalog]) => { if (active) { setEmail(me.user.email); setPlans(catalog.plans.filter(p => p.id !== "free")); } })
      .catch(() => { if (active) setStatus("سجّل الدخول عبر Google لطلب الاشتراك."); });
    return () => { active = false; };
  }, []);
  async function request(plan: Plan) {
    if (!email) return;
    setBusy(true); setStatus("");
    try {
      const result = await atlasFetch<{ reference: string; status: string; recipient?: string; phone?: string; support?: string }>(apiPath(`/billing/whish/${plan.id}/request`), {
        method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      setPayment(result);
      setStatus(ar ? `${result.reference}: الطلب قيد مراجعة المالك. طلب الدفع وحده لا يفعّل الاشتراك.` : `${result.reference}: pending owner review. A payment request does not activate a subscription.`);
    } catch { setStatus(ar ? "تعذّر إرسال طلب Whish. تحقق من الجلسة وطريقة الدفع." : "Unable to request Whish review. Check your session and payment method."); }
    finally { setBusy(false); }
  }
  return <section className="atlas-card atlas-subscription-flow" dir={ar ? "rtl" : "ltr"}>
    <div className="atlas-language-row"><button onClick={() => setLanguage("ar")}>العربية</button><span>|</span><button onClick={() => setLanguage("en")}>EN</button></div>
    <h1>{ar ? "اشتراكات أطلس عبر Whish" : "ATLAS subscriptions via Whish"}</h1>
    <p>{ar ? "Demo متاح لربط الحساب والمتابعة. ربط الحساب الحقيقي يحتاج اشتراكاً مدفوعاً نشطاً بعد مراجعة الإيصال. التنفيذ الحقيقي ما زال مقفلاً." : "Demo account connection and monitoring are available. A live account connection requires an active paid subscription after receipt review. Live execution remains locked."}</p>
    <a href="/connect">{ar ? "افتح صفحة ربط FxPro MT5" : "Open FxPro MT5 connection"}</a>
    {!email && <p><a className="atlas-primary-button" href="/login">{ar ? "تسجيل الدخول عبر Google" : "Sign in with Google"}</a></p>}
    <div className="atlas-plan-grid">{plans.map((plan) => <article className="atlas-card" key={plan.id}>
      <h2>{plan.name}</h2><strong>${plan.monthly_price} USD / {ar ? "شهر" : "month"}</strong>
      <ul>{plan.features.map((feature) => <li key={feature}>{ar ? (arabicFeature[feature] || feature) : feature}</li>)}</ul>
      <button type="button" className="atlas-primary-button" disabled={busy || !email} onClick={() => request(plan)}>{ar ? `طلب ${plan.name}` : `Request ${plan.name}`}</button>
    </article>)}</div>
    {payment && <aside className="atlas-card"><h2>{ar ? "بيانات الدفع عبر Whish" : "Whish payment details"}</h2>
      <p>{ar ? "المستلم" : "Recipient"}: {payment.recipient || "Contact support"}</p>
      <p>{ar ? "الهاتف" : "Phone"}: {payment.phone || "Contact support"}</p>
      <p>{ar ? "الدعم" : "Support"}: {payment.support || "Contact support"}</p>
      <p>{ar ? "اذكر رقم المرجع وأرفق إيصال Whish؛ التفعيل بعد مراجعة المالك فقط." : "Include your reference and receipt. Access starts only after owner review."}</p>
      <a className="atlas-primary-button" href={`mailto:imsamtaha.ai@gmail.com?subject=${encodeURIComponent(`ATLAS Whish ${payment.reference}`)}&body=${encodeURIComponent(`Reference: ${payment.reference}\nAccount: ${email}\nPlease attach your Whish receipt.`)}`}>{ar ? "إرسال إثبات الدفع" : "Email payment proof"}</a>
    </aside>}
    {status && <p role="status">{status}</p>}
  </section>;
}
