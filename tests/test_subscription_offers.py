from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.billing import router as billing_router
from app.billing.plans import PLANS


def test_signals_plan_is_99_and_manual_execution_only():
    plan = PLANS["watch"]
    assert plan.name == "ATLAS Signals & Setups"
    assert plan.monthly_price == 99
    assert "Telegram and email signal delivery" in plan.features
    assert "Manual execution by the customer" in plan.features
    assert plan.delivery_channels == ("telegram", "email")
    assert plan.execution_policy == "manual_customer"
    assert plan.message_language == "ar"
    assert "إشارة ATLAS" in plan.message_template_ar
    assert "التنفيذ: يدوي من قبل العميل" in plan.message_template_ar


def test_council_plan_is_149_and_requires_human_confirmation():
    plan = PLANS["reader"]
    assert plan.name == "ATLAS Council"
    assert plan.monthly_price == 149
    assert "Council-generated trade intents" in plan.features
    assert "Human confirmation before execution" in plan.features
    assert plan.delivery_channels == ("telegram", "email")
    assert plan.execution_policy == "human_confirmation"
    assert plan.message_language == "ar"
    assert "فرصة تداول من ATLAS Council" in plan.message_template_ar
    assert "الحالة: بانتظار تأكيدك" in plan.message_template_ar


def test_elite_plan_price_remains_299():
    plan = PLANS["pro"]
    assert plan.name == "ATLAS Elite"
    assert plan.monthly_price == 299


def test_public_offers_page_matches_signals_and_council_offers():
    app = FastAPI()
    app.include_router(billing_router)
    response = TestClient(app).get("/billing/offers")
    assert response.status_code == 200
    page = response.text
    assert "ATLAS Signals &amp; Setups" in page
    assert "$99" in page
    assert "Telegram" in page and "Email" in page
    assert "التنفيذ يدوي من قبل العميل" in page
    assert "ATLAS Council" in page
    assert "$149" in page
    assert "تأكيد العميل قبل التنفيذ" in page
    assert "/billing/whish/watch" in page
    assert "/billing/whish/reader" in page
