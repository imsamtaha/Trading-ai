from app.strategy.universe import classify_symbol, normalize_symbol, build_universe


def test_expanded_asset_classes():
    expected = {
        "XPTUSD": "METALS",
        "XPDUSD": "METALS",
        "AUDJPY": "FOREX",
        "CADJPY": "FOREX",
        "JP225": "INDICES",
        "HK50": "INDICES",
        "FRA40": "INDICES",
        "ADAUSD": "CRYPTO",
        "DOGEUSD": "CRYPTO",
        "LTCUSD": "CRYPTO",
    }

    for symbol, asset_class in expected.items():
        result = classify_symbol(symbol)
        assert result is not None
        assert result[0] == asset_class


def test_expanded_symbols_with_broker_suffixes():
    assert normalize_symbol("XPTUSDm") == "XPTUSD"
    assert normalize_symbol("AUDJPY.pro") == "AUDJPY"
    assert normalize_symbol("JP225.cash") == "JP225"
    assert normalize_symbol("ADAUSDm") == "ADAUSD"


def test_invalid_market_data_blocks_new_asset():
    result = build_universe([{
        "symbol": "XPTUSD",
        "bid": 0,
        "ask": 0,
        "point": 0.01,
        "tradeable": True,
        "visible": True,
    }])

    assert len(result) == 1
    assert result[0].tradeable is False
    assert result[0].opportunity_score == 0.0


def test_phase2_expanded_asset_classes():
    expected = {
        "EURAUD": "FOREX",
        "EURCAD": "FOREX",
        "AUS200": "INDICES",
        "EU50": "INDICES",
        "WHEAT": "COMMODITIES",
        "CORN": "COMMODITIES",
        "COCOA": "COMMODITIES",
        "COFFEE": "COMMODITIES",
        "AVAXUSD": "CRYPTO",
        "LINKUSD": "CRYPTO",
    }

    for symbol, asset_class in expected.items():
        result = classify_symbol(symbol)
        assert result is not None
        assert result[0] == asset_class


def test_phase2_invalid_market_data_stays_non_tradeable():
    symbols = ["WHEAT", "CORN", "AUS200", "AVAXUSD"]

    raw = [
        {
            "symbol": symbol,
            "bid": 0,
            "ask": 0,
            "point": 0.01,
            "tradeable": True,
            "visible": True,
        }
        for symbol in symbols
    ]

    result = build_universe(raw, top_n=20)

    assert len(result) == len(symbols)
    assert all(item.tradeable is False for item in result)
    assert all(item.opportunity_score == 0.0 for item in result)


def test_normalization_does_not_match_internal_fake_symbol():
    assert normalize_symbol("FAKEXAUUSDTEST") == "FAKEXAUUSDTEST"
    assert normalize_symbol("NOTAUDJPYFAKE") == "NOTAUDJPYFAKE"
    assert normalize_symbol("XXADAUSDZZ") == "XXADAUSDZZ"


def test_extended_alias_registry_and_suffixes():
    expected = {
        "PLATINUM": "XPTUSD",
        "PALLADIUM": "XPDUSD",
        "NIKKEI225": "JP225",
        "JPN225": "JP225",
        "CAC40": "FRA40",
        "ASX200": "AUS200",
        "STOXX50": "EU50",
        "EUROSTOXX50": "EU50",
    }

    for broker_symbol, canonical in expected.items():
        assert normalize_symbol(broker_symbol) == canonical
        assert normalize_symbol(broker_symbol + "m") == canonical

def test_diversify_universe_covers_available_asset_classes():
    from app.strategy.universe import UniverseSymbol, diversify_universe

    classes = ["METALS", "ENERGY", "FOREX", "INDICES", "CRYPTO", "COMMODITIES"]
    ranked = [
        UniverseSymbol(
            broker_symbol=f"TEST{i}",
            canonical_symbol=f"TEST{i}",
            asset_class=asset_class,
            priority=1,
            spread_points=1.0,
            spread_ratio=0.0001,
            tradeable=True,
            visible=True,
            opportunity_score=100.0 - i,
        )
        for i, asset_class in enumerate(classes)
    ]

    result = diversify_universe(ranked, top_n=6)

    assert len(result) == 6
    assert {x.asset_class for x in result} == set(classes)
