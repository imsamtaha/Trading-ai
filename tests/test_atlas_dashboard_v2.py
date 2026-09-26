import re

from app.billing.plans import PLANS
from app.dashboard import _atlas_ultimate_html


def test_customer_plans_use_v2_names_and_prices():
    assert PLANS["watch"].name == "ATLAS Starter"
    assert PLANS["watch"].monthly_price == 99
    assert PLANS["reader"].name == "ATLAS Pro"
    assert PLANS["reader"].monthly_price == 149
    assert PLANS["pro"].name == "ATLAS Elite"
    assert PLANS["pro"].monthly_price == 299
    assert all(plan.trial_days == 0 for plan in PLANS.values())


def test_dashboard_renders_only_v2_customer_prices():
    html = _atlas_ultimate_html()
    for price in ("$99", "$149", "$299"):
        assert price in html
    assert re.search(r"(?<!\d)\$29(?!\d)", html) is None
    assert re.search(r"(?<!\d)\$49(?!\d)", html) is None
    assert "ATLAS Starter" in html
    assert "ATLAS Pro" in html
    assert "ATLAS Elite" in html
