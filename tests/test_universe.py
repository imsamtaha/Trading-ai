from app.strategy.universe import build_universe, normalize_symbol


def test_normalize_common_broker_aliases():
    assert normalize_symbol("GOLD") == "XAUUSD"
    assert normalize_symbol("XAUUSDm") == "XAUUSD"
    assert normalize_symbol("USTEC.cash") == "NAS100"
    assert normalize_symbol("SPX500.pro") == "US500"
    assert normalize_symbol("SOLUSD") == "SOLUSD"


def test_build_universe_filters_and_ranks_tradeable_symbols():
    raw = [
        {"symbol": "GOLD", "bid": 2500.0, "ask": 2500.2, "point": 0.01, "tradeable": True, "visible": True},
        {"symbol": "EURUSD", "bid": 1.1000, "ask": 1.1001, "point": 0.00001, "tradeable": True, "visible": True},
        {"symbol": "BTCUSD", "bid": 60000.0, "ask": 60020.0, "point": 0.01, "tradeable": True, "visible": False},
        {"symbol": "UNKNOWN", "bid": 1.0, "ask": 1.1, "point": 0.01, "tradeable": True, "visible": True},
        {"symbol": "XAGUSD", "bid": 30.0, "ask": 30.1, "point": 0.001, "tradeable": False, "visible": True},
    ]

    universe = build_universe(raw, top_n=10)
    symbols = [item.canonical_symbol for item in universe]

    assert "XAUUSD" in symbols
    assert "EURUSD" in symbols
    assert "BTCUSD" in symbols
    assert "UNKNOWN" not in symbols
    xag = next(item for item in universe if item.canonical_symbol == "XAGUSD")
    assert xag.tradeable is False
    assert xag.opportunity_score == 0.0


def test_build_universe_deduplicates_canonical_symbols():
    raw = [
        {"symbol": "XAUUSD", "bid": 2500.0, "ask": 2500.1, "point": 0.01, "tradeable": True, "visible": True},
        {"symbol": "GOLD", "bid": 2500.0, "ask": 2500.2, "point": 0.01, "tradeable": True, "visible": True},
    ]
    universe = build_universe(raw, top_n=10)
    assert len([x for x in universe if x.canonical_symbol == "XAUUSD"]) == 1


def test_normalize_expanded_fxpro_assets():
    assert normalize_symbol("#Japan225") == "JP225"
    assert normalize_symbol("#HongKong50") == "HK50"
    assert normalize_symbol("#Euro50") == "EU50"
    assert normalize_symbol("#France40") == "FRA40"
    assert normalize_symbol("#US2000") == "US2000"
    assert normalize_symbol("AUDJPY") == "AUDJPY"
    assert normalize_symbol("EURCAD") == "EURCAD"
    assert normalize_symbol("CADJPY") == "CADJPY"
