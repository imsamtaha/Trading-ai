"""Contract-level tests for nine-seat PAPER-only ATLAS Council.

All example prices, numbers, outcomes and sources below are synthetic fixtures,
never verified market facts or trading recommendations.
"""
from datetime import datetime

import pytest

from app.intelligence.nine_seat_council import (
    INITIAL_SEATS,
    NineSeatPaperCouncil,
    classify_instrument,
    core_first,
    evaluator_scorecard,
)

TIMESTAMP = "2026-11-18T10:00:00+00:00"
AS_OF = datetime.fromisoformat("2026-11-18T10:05:00+00:00")


def make_council(symbol="XAUUSD", *, verified=True):
    return NineSeatPaperCouncil(
        instrument=symbol, timeframe="15m", timestamp=TIMESTAMP,
        snapshot_id="synthetic-paper-snapshot", verified_market_snapshot=verified,
    )


def independent_reports(*, sample_size=80):
    return {
        "macro": {
            "timestamp": TIMESTAMP, "bias": "NEUTRAL", "driver": "synthetic real yields example",
            "horizon": "next scheduled release", "confidence": 0.63,
        },
        "market_structure": {
            "timestamp": TIMESTAMP, "read": "synthetic range", "invalidation": "sample range invalidated",
            "higher_timeframe": "neutral", "confidence": 0.5,
            "setup_direction": "LONG", "liquidity_evidence": "synthetic liquidity sweep",
            "smc_confirmation": "synthetic change of character",
        },
        "quant": {
            "timestamp": TIMESTAMP, "confidence": 0.61, "sample_size": sample_size, "win_rate": 0.55,
            "average_rr": 1.7, "base_rate_source": "synthetic test ledger",
            "regime_note": "example regime may change",
        },
        "news_sentiment": {
            "timestamp": TIMESTAMP, "event_risk": "synthetic data cannot be used as calendar",
            "sentiment_skew": "neutral", "confidence": 0.5, "event_risk_acceptable": True,
        },
    }


def submit_initial(council, *, sample_size=80):
    reports = independent_reports(sample_size=sample_size)
    for seat in INITIAL_SEATS:
        council.submit_initial(seat, reports[seat], snapshot_id=council.snapshot_id)


def approve(council):
    council.submit_risk({
        "timestamp": TIMESTAMP, "status": "APPROVE", "reason": "all fictional checks passed",
        "approved_position_size_pct": 1.0,
        "checks": {
            "daily_loss": "PASS", "total_open_risk": "PASS",
            "correlation": "PASS", "position_size": "PASS", "event_exposure": "PASS",
        },
    })


def execution(council, *, stop=90.0, targets=None):
    council.submit_execution({
        "timestamp": TIMESTAMP, "entry": 100.0, "stop": stop,
        "take_profit": [130.0] if targets is None else targets,
        "order_type": "limit", "plan": "synthetic plan only",
        "hazards": "hypothetical spread and gap risk",
    })


def red_team(council, *, material_conflict=False):
    council.submit_red_team({
        "timestamp": TIMESTAMP, "material_conflict": material_conflict,
        "objection": "Synthetic snapshot may be stale or regime-shifted.",
        "failure_condition": "Model assumptions are wrong.",
    })


def chair(council, *, verdict="NO TRADE", conviction=4, pct=0.0):
    council.submit_chair({
        "timestamp": TIMESTAMP, "verdict": verdict, "conviction": conviction,
        "position_size_pct": pct,
        "rationale": "Macro and quant observations are inconclusive.",
        "drivers": ["macro", "quant"],
    })


def assert_wait(result):
    assert result["mode"] == "paper"
    assert result["decision"] == "WAIT"
    assert result["confidence"] == "UNSCORED"
    assert result["risk_pct"] == result["position_size_pct"] == 0
    assert result["entry"] is None and result["stop"] is None
    assert result["take_profit"] == []


def test_missing_reports_produce_dashboard_wait():
    council = make_council(verified=False)
    council.submit_initial("macro", independent_reports()["macro"], snapshot_id=council.snapshot_id)
    result = council.finalize(as_of=AS_OF)
    assert_wait(result)
    assert result["conviction"] is None
    assert result["evidence_issues"] == {
        "market_snapshot": "unverified",
        **dict.fromkeys(
            ("market_structure", "quant", "news_sentiment", "risk", "execution", "red_team", "chair"),
            "missing report",
        ),
    }


@pytest.mark.parametrize("timestamp, reason", [
    (None, "missing or invalid timestamp"),
    ("2026-11-18T09:49:59Z", "stale report"),
    ("2026-11-18T09:59:59Z", "report timestamp outside snapshot and evaluation times"),
    ("2026-11-18T10:05:01Z", "report timestamp outside snapshot and evaluation times"),
])
def test_invalid_report_time_blocks_directional_verdict(timestamp, reason):
    council = make_council()
    reports = independent_reports()
    reports["macro"]["timestamp"] = timestamp
    for seat, report in reports.items():
        council.submit_initial(seat, report, snapshot_id=council.snapshot_id)
    approve(council)
    execution(council)
    red_team(council)
    chair(council, verdict="LONG", pct=0.25)
    result = council.finalize(as_of=AS_OF)
    assert_wait(result)
    assert result["evidence_issues"] == {"macro": reason}


@pytest.mark.parametrize("seat,field,value,issue", [
    ("market_structure", "setup_direction", "SHORT", "market_structure.setup_direction"),
    ("market_structure", "liquidity_evidence", "", "market_structure.liquidity_evidence"),
    ("market_structure", "smc_confirmation", "", "market_structure.smc_confirmation"),
    ("news_sentiment", "event_risk_acceptable", False, "news_sentiment.event_risk_acceptable"),
    ("red_team", "material_conflict", True, "red_team.material_conflict"),
    ("execution", "take_profit", [129.9, 150], "execution.reward_to_risk"),
])
def test_directional_evidence_gates(seat, field, value, issue):
    council = make_council()
    reports = independent_reports()
    if seat in reports:
        reports[seat][field] = value
    for name, report in reports.items():
        council.submit_initial(name, report, snapshot_id=council.snapshot_id)
    approve(council)
    execution(council, targets=value if seat == "execution" else None)
    red_team(council, material_conflict=seat == "red_team")
    chair(council, verdict="LONG", pct=0.25)
    result = council.finalize(as_of=AS_OF)
    assert_wait(result)
    assert list(result["evidence_issues"]) == [issue]


def test_fully_formed_short_expires_after_snapshot_timeframe():
    council = make_council()
    reports = independent_reports()
    reports["market_structure"]["setup_direction"] = "SHORT"
    for seat, report in reports.items():
        council.submit_initial(seat, report, snapshot_id=council.snapshot_id)
    approve(council)
    execution(council, stop=110, targets=[70])
    red_team(council)
    chair(council, verdict="SHORT", pct=0.25)
    assert council.finalize(as_of=AS_OF)["decision"] == "SELL"
    expired = datetime.fromisoformat("2026-11-18T10:15:01+00:00")
    result = council.finalize(as_of=expired)
    assert_wait(result)
    assert result["evidence_issues"]["market_snapshot"] == "stale or future timestamp"


def test_all_seats_independent_and_final_paper_schema():
    council = make_council()
    submit_initial(council)
    approve(council)
    execution(council)
    red_team(council)
    chair(council, verdict="NO TRADE")
    result = council.finalize(as_of=AS_OF)
    assert result["mode"] == "paper"
    assert result["verdict"] == "NO TRADE"
    assert result["instrument"] == "XAUUSD"
    assert result["asset_class"] == "gold"
    assert result["entry"] is None and result["stop"] is None
    assert result["take_profit"] == []
    assert result["position_size_pct"] == 0
    assert result["seats"]["red_team"]["objection"]
    assert result["seats"]["quant"]["sample_size"] == 80
    assert result["chair_rationale"].startswith("SIMULATED/PAPER RECOMMENDATION")
    assert set(result) == {
        "instrument", "asset_class", "timeframe", "timestamp", "mode",
        "verdict", "conviction", "position_size_pct", "entry", "stop",
        "take_profit", "seats", "chair_rationale", "decision", "confidence",
        "risk_pct", "evidence_issues",
    }


def test_all_initial_seats_required_before_risk():
    council = make_council()
    council.submit_initial("macro", independent_reports()["macro"], snapshot_id=council.snapshot_id)
    with pytest.raises(ValueError, match="All four"):
        approve(council)


def test_cross_snapshot_input_rejected():
    council = make_council()
    with pytest.raises(ValueError, match="Mismatched"):
        council.submit_initial("macro", independent_reports()["macro"], snapshot_id="OTHER")


def test_initial_reports_cannot_change_after_risk():
    council = make_council()
    submit_initial(council)
    approve(council)
    with pytest.raises(ValueError, match="sealed"):
        council.submit_initial("macro", independent_reports()["macro"], snapshot_id=council.snapshot_id)


def test_duplicate_report_rejected():
    council = make_council()
    council.submit_initial("macro", independent_reports()["macro"], snapshot_id=council.snapshot_id)
    with pytest.raises(ValueError, match="duplicate"):
        council.submit_initial("macro", independent_reports()["macro"], snapshot_id=council.snapshot_id)


def test_final_risk_veto_cannot_be_overridden():
    council = make_council()
    submit_initial(council)
    council.submit_risk({
        "timestamp": TIMESTAMP, "status": "VETO", "reason": "risk limit exceeded (fictional)",
        "minimum_change": "wait for reset of simulated risk budget",
    })
    with pytest.raises(ValueError, match="requires explicit Risk APPROVE"):
        execution(council)
    with pytest.raises(ValueError, match="cannot overrule Risk"):
        chair(council, verdict="LONG", pct=0.1)
    chair(council, verdict="VETOED")
    result = council.finalize(as_of=AS_OF)
    assert result["verdict"] == "VETOED"
    assert result["entry"] is None
    assert result["stop"] is None
    assert result["take_profit"] == []
    assert "Minimum change" in result["chair_rationale"]
    assert result["seats"]["risk"]["status"] == "VETO"
    assert result["seats"]["execution"]["plan"] == ""


def test_veto_requires_specific_remedy():
    council = make_council()
    submit_initial(council)
    with pytest.raises(ValueError, match="minimum_change"):
        council.submit_risk({"status": "VETO", "reason": "synthetic risk violation"})


def test_risk_fails_closed_if_account_checks_missing():
    council = make_council()
    submit_initial(council)
    with pytest.raises(ValueError, match="every account-level check"):
        council.submit_risk({
            "status": "APPROVE", "reason": "hypothetical",
            "approved_position_size_pct": 1.0,
            "checks": {"daily_loss": "PASS"},
        })


def test_conditional_not_actionable_and_no_execution():
    council = make_council()
    submit_initial(council)
    council.submit_risk({
        "timestamp": TIMESTAMP, "status": "CONDITIONAL", "reason": "synthetic event risk",
        "conditions": "review after synthetic event",
    })
    with pytest.raises(ValueError, match="requires explicit Risk APPROVE"):
        execution(council)
    chair(council, verdict="NO TRADE")
    result = council.finalize(as_of=AS_OF)
    assert result["verdict"] == "NO TRADE"
    assert result["position_size_pct"] == 0
    assert "Not yet approved" in result["chair_rationale"]


def test_execution_and_red_team_required_before_chair_for_approval():
    council = make_council()
    submit_initial(council)
    approve(council)
    with pytest.raises(ValueError, match="Red Team"):
        chair(council)
    execution(council)
    with pytest.raises(ValueError, match="Red Team"):
        chair(council)
    red_team(council)
    chair(council)
    assert council.finalize(as_of=AS_OF)["verdict"] == "NO TRADE"


def test_execution_only_after_approved_risk():
    council = make_council()
    submit_initial(council)
    with pytest.raises(ValueError, match="requires explicit Risk APPROVE"):
        execution(council)


def test_red_team_objection_required():
    council = make_council()
    submit_initial(council)
    approve(council)
    execution(council)
    with pytest.raises(ValueError, match="red_team.objection"):
        council.submit_red_team({
            "objection": "", "failure_condition": "synthetic reversal",
        })


def test_no_objection_must_be_justified():
    council = make_council()
    submit_initial(council)
    approve(council)
    execution(council)
    with pytest.raises(ValueError, match="red_team.justification"):
        council.submit_red_team({
            "objection": "no objection", "failure_condition": "assumption fails",
        })


def test_chair_position_cannot_exceed_risk_cap():
    council = make_council()
    submit_initial(council)
    approve(council)
    execution(council)
    red_team(council)
    with pytest.raises(ValueError, match="exceeds approved Risk"):
        chair(council, verdict="LONG", pct=2.0)


def test_unverified_market_facts_never_create_directional_paper_proposal():
    council = make_council(verified=False)
    submit_initial(council)
    approve(council)
    execution(council)
    red_team(council)
    with pytest.raises(ValueError, match="verified snapshot"):
        chair(council, verdict="LONG", pct=0.2)
    chair(council, verdict="NO TRADE")
    assert "MARKET DATA UNVERIFIED" in council.finalize(as_of=AS_OF)["chair_rationale"]


def test_synthetic_directional_paper_preview_is_never_broker_execution():
    council = make_council()
    submit_initial(council)
    approve(council)
    execution(council)
    red_team(council)
    chair(council, verdict="LONG", pct=0.25)
    result = council.finalize(as_of=AS_OF)
    assert result["mode"] == "paper"
    assert result["entry"] == 100
    assert result["stop"] == 90
    assert result["take_profit"] == [130]
    assert result["decision"] == "BUY"
    assert result["evidence_issues"] == {}
    assert result["position_size_pct"] == 0.25
    assert not hasattr(council, "execute")
    assert not hasattr(council, "place_order")


@pytest.mark.parametrize("symbol,asset_class", [
    ("XAUUSD", "gold"), ("XAGUSD", "commodity"), ("NGAS", "commodity"),
    ("USOIL", "commodity"), ("WTI", "commodity"),
    ("UKOIL", "commodity"), ("BRENT", "commodity"), ("EUR/USD", "fx"),
    ("EURUSD", "fx"), ("US500", "equity_index"), ("US30", "equity_index"),
    ("NAS100", "equity_index"), ("AAPL", "equity"),
    ("XRP", "crypto"), ("SOL", "crypto"),
])
def test_instruments_are_classified_without_mislabeling_silver_gas(symbol, asset_class):
    assert classify_instrument(symbol) == asset_class


@pytest.mark.parametrize("frame", ["1m", "4h", "1d", "30s"])
def test_unsupported_independent_bias_timeframes_fail_closed(frame):
    with pytest.raises(ValueError, match="1m is entry-timing only"):
        NineSeatPaperCouncil(instrument="XAUUSD", timeframe=frame, timestamp=TIMESTAMP, snapshot_id="synthetic")


def test_crypto_requires_higher_conviction_and_stays_satellite():
    council = make_council("XRP")
    submit_initial(council)
    approve(council)
    execution(council)
    red_team(council)
    with pytest.raises(ValueError, match="conviction 5"):
        chair(council, verdict="LONG", conviction=4, pct=0.25)
    chair(council, verdict="LONG", conviction=5, pct=0.25)
    result = council.finalize(as_of=AS_OF)
    assert result["asset_class"] == "crypto"
    assert result["conviction"] == 5
    assert core_first([result]) == []


@pytest.mark.parametrize("core_count,crypto_count", [(0, 0), (3, 0), (4, 1), (5, 1), (8, 2)])
def test_shortlist_caps_crypto_and_keeps_waits_visible(core_count, crypto_count):
    core = [
        {"mode": "paper", "instrument": symbol, "asset_class": classify_instrument(symbol),
         "verdict": "LONG"}
        for symbol in ("EURUSD", "USOIL", "XAGUSD", "AAPL", "XAUUSD", "MSFT", "UKOIL", "NAS100")
    ][:core_count]
    eligible_crypto = [
        {"mode": "paper", "instrument": symbol, "asset_class": "crypto",
         "verdict": "SHORT", "conviction": 5}
        for symbol in ("XRP", "SOL", "SOLUSD")
    ]
    crypto_wait = make_council("XRP").finalize(as_of=AS_OF)
    crypto_veto = {**crypto_wait, "verdict": "VETOED"}
    core_wait = make_council("XAUUSD").finalize(as_of=AS_OF)
    ranked = core_first([
        {**eligible_crypto[0], "conviction": 4},
        *eligible_crypto, crypto_wait, crypto_veto, core_wait, *core,
        {**core_wait, "mode": "live", "verdict": "LONG"},
    ])
    assert ranked[-2:] == [crypto_wait, crypto_veto]
    assert ranked[core_count + 1:-2] == eligible_crypto[:crypto_count]
    assert ranked[0]["asset_class"] == "gold"
    assert len(ranked) == core_count + crypto_count + 3


def test_quant_low_sample_is_explicitly_annotated():
    council = make_council()
    submit_initial(council, sample_size=12)
    approve(council)
    execution(council)
    red_team(council)
    chair(council)
    assert "n<30: anecdotal" in council.finalize(as_of=AS_OF)["chair_rationale"]


def test_fails_on_nonfinite_or_malformed_quant_metrics():
    council = make_council()
    wrong = independent_reports()["quant"]
    wrong["confidence"] = float("nan")
    with pytest.raises(ValueError, match="finite"):
        council.submit_initial("quant", wrong, snapshot_id=council.snapshot_id)


def test_evaluator_weekly_not_a_voting_seat_and_never_counts_unsettled():
    records = (
        [{"mode": "paper", "settled": True, "verdict": "LONG", "correct": True,
          "conviction": 5, "asset_class": "gold"} for _ in range(4)] +
        [{"mode": "paper", "settled": True, "verdict": "SHORT", "correct": False,
          "conviction": 4, "asset_class": "crypto"} for _ in range(2)] +
        [{"mode": "paper", "settled": False, "verdict": "LONG", "correct": True,
          "conviction": 5, "asset_class": "gold"}] +
        [{"mode": "live", "settled": True, "verdict": "LONG", "correct": True,
          "conviction": 5, "asset_class": "gold"}]
    )
    scorecard = evaluator_scorecard(records)
    assert scorecard["mode"] == "paper"
    assert scorecard["cadence"] == "weekly"
    assert scorecard["settled_paper_count"] == 6
    assert scorecard["status"] == "INSUFFICIENT_SETTLED_PAPER_SAMPLES"
    assert scorecard["conviction_calibration"]["5"] == {"n": 4, "hit_rate": 1.0}
    assert scorecard["asset_class_scorecard"]["crypto"] == {"n": 2, "hit_rate": 0.0}
    assert scorecard["evaluator_votes"] is False
    assert scorecard["broker_execution_allowed"] is False


def test_risk_veto_requires_no_chair_to_produce_wait():
    council = make_council()
    submit_initial(council)
    council.submit_risk({
        "timestamp": TIMESTAMP, "status": "VETO", "reason": "synthetic veto",
        "minimum_change": "adjust simulated risk",
    })
    result = council.finalize(as_of=AS_OF)
    assert_wait(result)
    assert result["verdict"] == "VETOED"
    assert result["evidence_issues"] == {}
    assert "synthetic veto" in result["chair_rationale"]


def test_no_direct_action_methods_or_broker_integration():
    council = make_council()
    for forbidden in ("execute_trade", "place_order", "connect_mt5", "enable_live", "update_weights", "train"):
        assert not hasattr(council, forbidden)
