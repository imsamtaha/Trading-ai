from types import SimpleNamespace

from app import billing


class FakeSessions:
    def __init__(self):
        self.params = None

    def create(self, params):
        self.params = params
        return {"url": "https://checkout.stripe.test/session"}


class FakeStripe:
    def __init__(self):
        self.sessions = FakeSessions()
        self.client = SimpleNamespace(v1=SimpleNamespace(checkout=SimpleNamespace(sessions=self.sessions)))

    def StripeClient(self, key):
        assert key == "rk_test_atlas"
        return self.client


def test_checkout_uses_subscription_price_and_three_day_trial(monkeypatch):
    fake_stripe = FakeStripe()
    monkeypatch.setattr(billing, "stripe", fake_stripe)
    monkeypatch.setenv("STRIPE_RESTRICTED_KEY", "rk_test_atlas")
    monkeypatch.setenv("STRIPE_PRICE_READER", "price_reader")

    result = billing.create_checkout_session("reader", "https://atlas.example")

    assert result["checkout_url"] == "https://checkout.stripe.test/session"
    assert fake_stripe.sessions.params["mode"] == "subscription"
    assert fake_stripe.sessions.params["line_items"] == [{"price": "price_reader", "quantity": 1}]
    assert fake_stripe.sessions.params["subscription_data"]["trial_period_days"] == 3
    assert "payment_method_types" not in fake_stripe.sessions.params
