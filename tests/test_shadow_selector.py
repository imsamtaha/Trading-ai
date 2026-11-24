from datetime import datetime, timedelta, timezone
from app.strategy.universe import build_universe, diversify_universe
from app.intelligence.shadow_selector import ShadowSelector

def raw(symbol):
    return dict(symbol=symbol, bid=100, ask=100.01, point=.01, tradeable=True, visible=True)

def test_equities_and_crypto_are_discovered():
    result = build_universe([raw("AAPL"), raw("TSLA"), raw("SOLUSD"), raw("XRPUSD")], 100)
    assert {x.asset_class for x in result} == {"STOCKS", "CRYPTO"}

def test_diversification_round_robins_instead_of_filling_forex():
    source = build_universe([raw(s) for s in ["EURUSD","GBPUSD","USDJPY","AUDUSD","BTCUSD","ETHUSD","AAPL","TSLA"]], 100)
    selected = diversify_universe(source, 6)
    assert [x.asset_class for x in selected].count("FOREX") == 2
    assert [x.asset_class for x in selected].count("STOCKS") == 2
    assert [x.asset_class for x in selected].count("CRYPTO") == 2

def trades(n=120):
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return [dict(id=str(i), symbol="EURUSD", direction="LONG", strategy="CONTINUATION_5M",
        confidence=90 if i%2 else 50, status="CLOSED", r_multiple=2 if i%2 else -1,
        opened_at=(start+timedelta(hours=i)).isoformat(),
        closed_at=(start+timedelta(hours=i, minutes=5)).isoformat()) for i in range(n)]

def test_shadow_waits_for_independent_days_and_samples():
    model = ShadowSelector()
    report = model.fit(trades(20))
    assert report["status"] == "INSUFFICIENT_DATA"
    assert model.predict(trades(1)[0])["probability"] is None
    assert report["broker_execution_allowed"] is False

def test_shadow_purges_overlapping_positions_and_stays_observational():
    rows = trades()
    rows[0]["closed_at"] = rows[100]["closed_at"]
    model = ShadowSelector()
    report = model.fit(rows)
    assert report["purged_train"] >= 1
    assert report["status"] == "SHADOW_ONLY"
    prediction = model.predict(rows[-1])
    assert 0 <= prediction["probability"] <= 1
    assert prediction["changes_trade_decision"] is False
    assert report["test"]["samples"] == 24

def test_shadow_rejects_future_labels_and_live_outcomes():
    rows = trades()
    rows[0]["broker_execution_allowed"] = True
    rows[1]["r_multiple"] = float("nan")
    rows[2]["closed_at"] = "2099-01-01T00:00:00+00:00"
    rows.append(rows[3].copy())
    report = ShadowSelector().fit(rows)
    assert report["invalid_records"] == 3
    assert report["duplicate_records"] == 1

def test_shadow_features_cannot_read_outcome():
    model = ShadowSelector()
    row = trades(1)[0]
    original = model.features(row)
    row.update(r_multiple=999, exit=999, risk_normalized_pnl=999)
    assert model.features(row) == original
