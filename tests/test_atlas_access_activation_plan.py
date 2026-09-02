from app.atlas.subscription import PLANS, get_plan


def test_catalog_contains_three_paid_plans():
    assert [p.id for p in PLANS] == ["starter", "pro", "elite"]
    assert get_plan("pro").monthly_price == 59
