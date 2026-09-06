from app.billing.stripe_checkout import StripeBilling


def test_reader_checkout_uses_three_day_trial_and_dynamic_payment_methods(monkeypatch):
    billing = StripeBilling(secret_key="sk_test", app_url="https://atlas.example")
    monkeypatch.setenv("ATLAS_STRIPE_PRICE_READER", "price_reader")

    class SessionService:
        def create(self, params):
            assert params["mode"] == "subscription"
            assert params["subscription_data"]["trial_period_days"] == 3
            assert "payment_method_types" not in params
            assert params["line_items"] == [{"price": "price_reader", "quantity": 1}]
            return {"id": "cs_test_1", "url": "https://checkout.stripe.test/cs_test_1"}

    class Client:
        class V1:
            class Checkout:
                sessions = SessionService()
            checkout = Checkout()
        v1 = V1()

    monkeypatch.setattr(billing, "_client", lambda: Client())

    session = billing.create_checkout_session("reader")

    assert session["plan_id"] == "reader"
    assert session["url"].startswith("https://checkout.stripe.test/")


def test_unknown_plan_is_rejected():
    billing = StripeBilling(secret_key="sk_test", app_url="https://atlas.example")

    try:
        billing.plan("unknown")
    except Exception as exc:
        assert "Unknown subscription plan" in str(exc)
    else:
        raise AssertionError("Unknown plans must be rejected")
