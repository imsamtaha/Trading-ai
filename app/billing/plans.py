"""ATLAS subscription plans shared by the payment flows."""
from dataclasses import dataclass


SIGNALS_MESSAGE_AR = """إشارة ATLAS

الأصل: {symbol}
الاتجاه: {direction}
منطقة الدخول: {entry}
وقف الخسارة: {stop_loss}
الهدف الأول: {target_1}
الهدف الثاني: {target_2}
درجة الثقة: {confidence}
سياق المخاطر: {risk_context}

الحالة: إشارة فقط
التنفيذ: يدوي من قبل العميل

يرجى مراجعة الصفقة وإدارة المخاطر قبل التنفيذ."""

COUNCIL_MESSAGE_AR = """فرصة تداول من ATLAS Council

الأصل: {symbol}
الاتجاه: {direction}
الدخول: {entry}
وقف الخسارة: {stop_loss}
الهدف: {target}
المخاطر: {risk_context}
درجة الثقة: {confidence}

الحالة: بانتظار تأكيدك

[ تأكيد الصفقة ]
[ رفض الصفقة ]"""


@dataclass(frozen=True)
class SubscriptionPlan:
    id: str
    name: str
    monthly_price: int
    trial_days: int
    features: tuple[str, ...]
    delivery_channels: tuple[str, ...] = ()
    execution_policy: str = "none"
    message_language: str = "ar"
    message_template_ar: str = ""


PLANS: dict[str, SubscriptionPlan] = {
    "watch": SubscriptionPlan(
        id="watch",
        name="ATLAS Signals & Setups",
        monthly_price=99,
        trial_days=0,
        features=(
            "Council-generated signals and setups",
            "Entry, stop and target levels",
            "Risk and confidence context",
            "Telegram and email signal delivery",
            "Manual execution by the customer",
        ),
        delivery_channels=("telegram", "email"),
        execution_policy="manual_customer",
        message_language="ar",
        message_template_ar=SIGNALS_MESSAGE_AR,
    ),
    "reader": SubscriptionPlan(
        id="reader",
        name="ATLAS Council",
        monthly_price=149,
        trial_days=0,
        features=(
            "Everything in Signals & Setups",
            "Council-generated trade intents",
            "Capital Guardian and deterministic risk checks",
            "Position monitoring and Council alerts",
            "Human confirmation before execution",
        ),
        delivery_channels=("telegram", "email"),
        execution_policy="human_confirmation",
        message_language="ar",
        message_template_ar=COUNCIL_MESSAGE_AR,
    ),
    "pro": SubscriptionPlan(
        id="pro",
        name="ATLAS Elite",
        monthly_price=299,
        trial_days=0,
        features=(
            "Everything in ATLAS Council",
            "Advanced multi-asset analysis",
            "Advanced risk and position monitoring",
            "Exit and stop alerts",
            "Priority intelligence briefings",
            "Advanced AI chart and assistant features",
        ),
        delivery_channels=("telegram", "email"),
        execution_policy="human_confirmation",
        message_language="ar",
        message_template_ar=COUNCIL_MESSAGE_AR,
    ),
}


def public_plans() -> tuple[SubscriptionPlan, ...]:
    return tuple(PLANS.values())
