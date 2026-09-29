"""Public ATLAS subscription offer page."""

import html

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app.billing.plans import PLANS

router = APIRouter(prefix="/billing", tags=["billing"])


def _feature_list(items: tuple[str, ...]) -> str:
    return "".join(f"<li>{html.escape(item)}</li>" for item in items)


@router.get("/offers", response_class=HTMLResponse)
def offers_page() -> HTMLResponse:
    signals = PLANS["watch"]
    council = PLANS["reader"]
    elite = PLANS["pro"]
    page = f"""<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ATLAS | خطط الاشتراك</title>
<style>
:root{{--bg:#f7f4ee;--panel:#fffaf2;--ink:#151515;--muted:#6f6a61;--line:#ded7ca;--orange:#f07a18}}
*{{box-sizing:border-box}}body{{margin:0;background:radial-gradient(circle at 90% 0,#ffe1bf 0,transparent 30%),var(--bg);color:var(--ink);font-family:Tahoma,Arial,sans-serif;line-height:1.65}}
main{{width:min(1120px,calc(100% - 28px));margin:36px auto 64px}}.eyebrow{{font-size:12px;letter-spacing:.14em;color:var(--orange);font-weight:800}}h1{{font-size:clamp(34px,7vw,68px);line-height:1.05;margin:8px 0 12px}}.lead{{max-width:760px;color:var(--muted);font-size:16px}}
.grid{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px;margin-top:28px}}.card{{background:rgba(255,250,242,.93);border:1px solid var(--line);border-radius:24px;padding:24px;box-shadow:0 20px 55px #4d2a0b12;display:flex;flex-direction:column;gap:14px}}.card.featured{{border-color:#f07a1866;box-shadow:0 24px 70px #f07a1820}}.name{{font-size:22px;font-weight:900}}.price{{font-size:42px;font-weight:950;letter-spacing:-.04em}}.price small{{font-size:13px;color:var(--muted);font-weight:700}}ul{{padding:0 20px 0 0;margin:0;color:#3e3a34}}li{{margin:7px 0}}.policy{{padding:12px 14px;border-radius:14px;background:#fff;border:1px solid var(--line);font-size:13px}}.btn{{display:inline-block;text-decoration:none;text-align:center;padding:12px 16px;border-radius:12px;background:var(--orange);color:white;font-weight:900;margin-top:auto}}.btn.secondary{{background:#171717}}.note{{margin-top:22px;padding:16px;border:1px solid var(--line);border-radius:16px;color:var(--muted);background:#fffaf2cc}}
@media(max-width:860px){{.grid{{grid-template-columns:1fr}}}}
</style>
</head>
<body><main>
<div class="eyebrow">ATLAS TRADING INTELLIGENCE</div>
<h1>اختر طريقة استخدام ATLAS</h1>
<p class="lead">خطتان واضحتان بدون لف ودوران: إشارات تُنفَّذ يدوياً، أو ATLAS Council مع تأكيد العميل قبل التنفيذ. لأن تحويل التسعير إلى أحجية كان ناقصنا فعلاً.</p>
<section class="grid">
<article class="card">
<div class="name">{html.escape(signals.name)}</div>
<div class="price">${signals.monthly_price}<small> / شهرياً</small></div>
<p>يحلّل ATLAS Council السوق ويرسل الإشارات والإعدادات باللغة العربية عبر Telegram أو Email.</p>
<ul>{_feature_list(signals.features)}</ul>
<div class="policy"><strong>طريقة التنفيذ:</strong> التنفيذ يدوي من قبل العميل. لا يتم إرسال أوامر للوسيط ضمن هذه الخطة.</div>
<a class="btn" href="/billing/whish/watch">الاشتراك عبر Whish</a>
</article>
<article class="card featured">
<div class="name">{html.escape(council.name)}</div>
<div class="price">${council.monthly_price}<small> / شهرياً</small></div>
<p>ATLAS Council يحضّر قرار التداول، يمرّره عبر الحماية والمخاطر، ثم ينتظر تأكيد العميل قبل التنفيذ.</p>
<ul>{_feature_list(council.features)}</ul>
<div class="policy"><strong>طريقة التنفيذ:</strong> تأكيد العميل قبل التنفيذ.</div>
<a class="btn secondary" href="/billing/whish/reader">تفعيل ATLAS Council</a>
</article>
<article class="card">
<div class="name">{html.escape(elite.name)}</div>
<div class="price">${elite.monthly_price}<small> / شهرياً</small></div>
<p>طبقة متقدمة للمراقبة والتحليل متعدد الأصول والتنبيهات ذات الأولوية.</p>
<ul>{_feature_list(elite.features)}</ul>
<a class="btn" href="/billing/whish/pro">الاشتراك عبر Whish</a>
</article>
</section>
<div class="note">الدفع لا يفعّل ATLAS Council تلقائياً. يبقى الوصول مقفلاً حتى مراجعة الدفع وتأكيد الاشتراك. التداول ينطوي على مخاطر ولا توجد نتائج أو أرباح مضمونة.</div>
</main></body></html>"""
    return HTMLResponse(page)
