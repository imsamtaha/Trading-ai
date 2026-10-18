from copy import deepcopy

import pytest

from app.intelligence.autonomy_governor import (
    assess_paper_autonomy,
    record_assessment,
    score_decision,
    validate_candles,
)


def candles():
    return [
        {"time": 10000 + 300 * i, "open": 100, "high": 102, "low": 99, "close": 101}
        for i in range(6)
    ]


def evidence():
    return {
        "kill_switch": "ACTIVE",
        "api_healthy": True,
        "snapshot_fresh": True,
        "data_quality_valid": True,
        "portfolio_exposure_ok": True,
        "correlation_ok": True,
        "event_risk": "NORMAL",
        "volatility": "NORMAL",
        "senior_risk": {"assessment": "RISK_ACCEPTABLE"},
        "timeframes": {
            frame: {"direction": "LONG", "risk_approved": True}
            for frame in ("1h", "30m", "15m", "5m")
        },
        "quality_components": {
            "market_structure": 22,
            "momentum": 18,
            "timeframe_alignment": 19,
            "volatility": 13,
            "liquidity": 8,
            "signal_quality": 9,
            "risk_reward": 8,
        },
        "calibration": {
            "probability": 0.61,
            "out_of_sample_samples": 250,
            "validated_out_of_sample": True,
            "profile_id": "paper-test-v1",
        },
    }


def test_fresh_consistent_candles():
    result = validate_candles(
        candles(), interval_seconds=300, observed_at=11560,
        max_age_seconds=300, bid=100, ask=100.05, max_spread_fraction=.002,
    )
    assert result["valid"] is True


@pytest.mark.parametrize("alter,reason", [
    (lambda rows: rows.__setitem__(3, rows[2].copy()), "DUPLICATE_CANDLES"),
    (lambda rows: rows[3].update(time=rows[2]["time"] + 600), "MISSING_CANDLES"),
    (lambda rows: rows[3].update(high=99), "INCONSISTENT_OHLC"),
    (lambda rows: rows[3].update(close=float("nan")), "INVALID_CANDLE"),
])
def test_bad_bars_fail_closed(alter, reason):
    rows = candles()
    alter(rows)
    result = validate_candles(rows, interval_seconds=300, observed_at=11560, max_age_seconds=300)
    assert result["valid"] is False
    assert reason in result["reason_codes"]


def test_stale_future_and_spread_fail_closed():
    assert "STALE_OR_FUTURE_DATA" in validate_candles(
        candles(), interval_seconds=300, observed_at=15000, max_age_seconds=300,
    )["reason_codes"]
    assert "STALE_OR_FUTURE_DATA" in validate_candles(
        candles(), interval_seconds=300, observed_at=11000, max_age_seconds=300,
    )["reason_codes"]
    assert "SPREAD_TOO_WIDE" in validate_candles(
        candles(), interval_seconds=300, observed_at=11560, max_age_seconds=300,
        bid=100, ask=110, max_spread_fraction=.002,
    )["reason_codes"]


def test_missing_and_malformed_bars_fail_closed():
    assert validate_candles(None, interval_seconds=300, observed_at=11560,
                            max_age_seconds=300)["valid"] is False
    assert validate_candles(candles()[:2], interval_seconds=300, observed_at=11560,
                            max_age_seconds=300)["valid"] is False


def test_score_is_not_win_probability():
    q = score_decision(evidence()["quality_components"])
    assert (q["points"], q["maximum"], q["probability"]) == (97, 110, None)


def test_approved_evidence_produces_non_executable_paper_candidate():
    original = evidence()
    copy = deepcopy(original)
    result = assess_paper_autonomy(original)
    assert result["decision"] == "LONG"
    assert result["paper_candidate_only"] is True
    assert result["calibrated_probability"] == .61
    assert result["broker_execution_allowed"] is False
    assert result["paper_execution_performed"] is False
    assert original == copy


@pytest.mark.parametrize("change,code", [
    ({"kill_switch": "HALTED"}, "KILL_SWITCH_HALTED"),
    ({"kill_switch": "DEFENSIVE"}, "KILL_SWITCH_DEFENSIVE"),
    ({"api_healthy": False}, "API_HEALTHY_NOT_VERIFIED"),
    ({"snapshot_fresh": False}, "SNAPSHOT_FRESH_NOT_VERIFIED"),
    ({"data_quality_valid": False}, "DATA_QUALITY_VALID_NOT_VERIFIED"),
    ({"portfolio_exposure_ok": False}, "PORTFOLIO_EXPOSURE_OK_NOT_VERIFIED"),
    ({"correlation_ok": False}, "CORRELATION_OK_NOT_VERIFIED"),
    ({"event_risk": "EXTREME"}, "EVENT_RISK_UNACCEPTABLE"),
    ({"volatility": "EXTREME"}, "VOLATILITY_NOT_NORMAL"),
    ({"senior_risk": {"assessment": "RISK_REJECT"}}, "SENIOR_RISK_VETO"),
    ({"calibration": None}, "CALIBRATION_UNVERIFIED"),
    ({"quality_components": {}}, "QUALITY_NOT_VERIFIED"),
    ({"timeframes": {}}, "MTF_INCOMPLETE"),
])
def test_every_veto_returns_no_trade(change, code):
    input_data = evidence()
    input_data.update(change)
    result = assess_paper_autonomy(input_data)
    assert result["decision"] == "NO_TRADE"
    assert code in result["reason_codes"]
    assert result["broker_execution_allowed"] is False


def test_mtf_disagreement_and_frame_risk_are_vetoes():
    inp = evidence()
    inp["timeframes"]["5m"]["direction"] = "SHORT"
    assert "MTF_DISAGREEMENT" in assess_paper_autonomy(inp)["reason_codes"]
    inp = evidence()
    inp["timeframes"]["1h"]["risk_approved"] = False
    assert "MTF_RISK_VETO" in assess_paper_autonomy(inp)["reason_codes"]


def test_unverified_calibration_cannot_be_used_as_probability():
    inp = evidence()
    inp["calibration"]["validated_out_of_sample"] = False
    result = assess_paper_autonomy(inp)
    assert result["calibrated_probability"] is None
    assert result["decision"] == "NO_TRADE"


def test_paper_assessment_can_be_audited_without_broker_access(tmp_path):
    path = tmp_path / "paper-governance.jsonl"
    assessment = assess_paper_autonomy(evidence())
    saved = record_assessment(assessment, symbol="EURUSD", snapshot_id="test", path=str(path))
    assert saved["event"] == "AUTONOMY_SAFETY_ASSESSMENT"
    assert saved["environment"] == "PAPER"
    assert saved["broker_execution_allowed"] is False
    assert path.is_file()
    with pytest.raises(ValueError):
        record_assessment({**assessment, "broker_execution_allowed": True},
                          symbol="EURUSD", snapshot_id="bad", path=str(path))
