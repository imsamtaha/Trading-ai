from app.dashboard import api as dashboard_api


def test_chart_data_returns_bounded_candles(monkeypatch):
    calls = {}

    def fake_get_candles(symbol, interval, limit):
        calls.update(symbol=symbol, interval=interval, limit=limit)
        return {
            "symbol": symbol,
            "interval": interval,
            "count": 2,
            "candles": [
                {"open_time": 1, "open": 10, "high": 12, "low": 9, "close": 11, "volume": 5, "close_time": 2},
                {"open_time": 2, "open": 11, "high": 13, "low": 10, "close": 12, "volume": 6, "close_time": 3},
            ],
        }

    monkeypatch.setattr(dashboard_api, "get_candles", fake_get_candles)
    payload = dashboard_api.chart_data(symbol="xauusd", interval="15m", limit=120)

    assert calls == {"symbol": "XAUUSD", "interval": "15m", "limit": 120}
    assert payload["symbol"] == "XAUUSD"
    assert payload["count"] == 2
    assert payload["candles"][1]["close"] == 12


def test_chart_data_rejects_unsupported_interval():
    try:
        dashboard_api.chart_data(symbol="XAUUSD", interval="2m", limit=120)
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 400
    else:
        raise AssertionError("Unsupported interval should fail")
