from types import SimpleNamespace

from app.billing.stripe_checkout import StripeBilling


class FakeSessions:
    def __init__(self):
        self.params = None

    def create(self, params):
        self.params = params
        return {"id": "cs_test_atlas", "url": "https://checkout.stripe.test/session"}


def test_checkout_uses_subscription_price_and_three_day_trial(monkeypatch):
    sessions = FakeSessions()
    client = SimpleNamespace(v1=SimpleNamespace(checkout=SimpleNamespace(sessions=sessions)))
    monkeypatch.setenv("ATLAS_STRIPE_PRICE_READER", "price_reader")
    billing = StripeBilling(secret_key="rk_test_atlas", app_url="https://atlas.example")
    monkeypatch.setattr(billing, "_client", lambda: client)

    result = billing.create_checkout_session("reader")

    assert result["url"] == "https://checkout.stripe.test/session"
    assert sessions.params["mode"] == "subscription"
    assert sessions.params["line_items"] == [{"price": "price_reader", "quantity": 1}]
    assert sessions.params["subscription_data"]["trial_period_days"] == 3
    assert "payment_method_types" not in sessions.params
