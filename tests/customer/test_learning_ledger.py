from app.customer.realtime.learning import LearningLedger


def test_weights_update_only_after_ten_closed_demo_outcomes(tmp_path):
    path = tmp_path / "learned.json"
    ledger = LearningLedger(path, account_id="demo-1")
    assert ledger.weights() == {}
    for ticket in range(1, 11):
        ledger.record(ticket, "BUY", {"technical": "LONG", "regime": "SHORT"})
        if ticket == 1:
            assert ledger.weights() == {}
        ledger.settle(ticket, 2.0)
        ledger.settle(ticket, -2.0)  # duplicate cannot rewrite the outcome
    saved = LearningLedger(path, account_id="demo-1")
    assert saved.weights()["technical"] > saved.weights()["regime"]
    assert saved.samples("technical") == 10
    assert saved.samples("regime") == 10


def test_learning_fails_closed_for_wrong_account_and_ignores_unclosed_trade(tmp_path):
    path = tmp_path / "learned.json"
    ledger = LearningLedger(path, account_id="demo-1")
    ledger.record(123, "SELL", {"technical": "SHORT"})
    assert LearningLedger(path, account_id="demo-1").weights() == {}
    try:
        LearningLedger(path, account_id="demo-2")
    except ValueError:
        pass
    else:
        raise AssertionError("Account switch must reject the learning ledger")
