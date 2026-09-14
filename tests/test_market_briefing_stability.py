from datetime import datetime, timezone

from app.dashboard.market_briefing import MarketBriefingService, _freshness


def test_freshness_classifies_fresh_delayed_and_stale(monkeypatch):
    monkeypatch.setenv("ATLAS_MARKET_FRESH_SECONDS", "900")
    monkeypatch.setenv("ATLAS_MARKET_STALE_SECONDS", "86400")
    now = datetime.now(timezone.utc).timestamp()

    assert _freshness(now - 60)[1:] == ("FRESH", True)
    assert _freshness(now - 3600)[1:] == ("DELAYED", True)
    assert _freshness(now - 90000)[1:] == ("STALE", False)


def test_market_board_cache_avoids_duplicate_provider_calls(monkeypatch):
    monkeypatch.setenv("ATLAS_MARKET_CACHE_SECONDS", "60")
    service = MarketBriefingService()
    calls = 0

    def quote(symbol):
        nonlocal calls
        calls += 1
        return 100.0, 1.0, 1.0, datetime.now(timezone.utc).isoformat(), "FRESH", True

    monkeypatch.setattr(service, "_chart_quote", quote)
    first = service.market_board()
    second = service.market_board()

    assert first == second
    assert calls == 10


def test_stale_quotes_are_excluded_from_breadth(monkeypatch):
    service = MarketBriefingService()
    board = [
        {"available": True, "fresh": True, "change_percent": -1.0},
        {"available": True, "fresh": True, "change_percent": -0.5},
        {"available": True, "fresh": False, "change_percent": 9.0},
    ]
    monkeypatch.setattr(service, "market_board", lambda: board)
    monkeypatch.setattr(service, "headlines", lambda: [])

    result = service.briefing()
    analysis = result["market_analysis"]

    assert analysis["breadth"] == "BEARISH"
    assert analysis["tracked"] == 3
    assert analysis["usable"] == 2
    assert analysis["stale"] == 1
    assert analysis["rising"] == 0
    assert analysis["falling"] == 2


def test_all_stale_quotes_degrade_status_and_hide_breadth(monkeypatch):
    service = MarketBriefingService()
    board = [{"available": True, "fresh": False, "change_percent": 5.0}]
    monkeypatch.setattr(service, "market_board", lambda: board)
    monkeypatch.setattr(service, "headlines", lambda: [])

    result = service.briefing()

    assert result["status"] == "DEGRADED"
    assert result["market_analysis"]["breadth"] == "UNAVAILABLE"
    assert result["market_analysis"]["usable"] == 0
    assert result["market_analysis"]["stale"] == 1
