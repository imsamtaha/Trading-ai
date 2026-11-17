"""The offline runner must execute the paper pipeline without MT5 or a network."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "atlas_offline_cycle.py"


def _run(tmp_path, *extra):
    return subprocess.run(
        [sys.executable, str(RUNNER), "--ledger", str(tmp_path / "ledger.json"),
         "--reset-ledger", *extra],
        capture_output=True, text=True, cwd=ROOT,
    )


def test_offline_cycle_runs_the_pipeline_and_never_claims_live_data(tmp_path):
    result = _run(tmp_path, "--symbols", "XAUUSD,EURUSD", "--candles", "120",
                  "--settle-bars", "60")
    assert result.returncode == 0, result.stderr

    report = json.loads(result.stdout)
    assert report["synthetic_data"] is True
    assert report["data_source"] == "SYNTHETIC_LOCAL"
    assert report["live_orders_sent"] is False
    assert report["mode"] == "PAPER_DEMO"
    assert report["summary"]["symbols_evaluated"] == 2
    # Deterministic gates must reach a decision for every symbol.
    assert sum(report["summary"]["status_counts"].values()) == 2
    assert report["readiness"]["automatic_live_activation"] is False


def test_offline_cycle_is_deterministic_for_a_fixed_seed(tmp_path):
    first = _run(tmp_path, "--symbols", "XAUUSD", "--candles", "120",
                 "--settle-bars", "60", "--seed", "11")
    second = _run(tmp_path, "--symbols", "XAUUSD", "--candles", "120",
                  "--settle-bars", "60", "--seed", "11")
    assert first.returncode == second.returncode == 0

    def fingerprint(payload: str) -> dict:
        report = json.loads(payload)
        symbol = report["events"][0]
        return {
            "status": symbol["status"],
            "price": symbol["price"],
            "trend": symbol["trend"],
            "decision": symbol["decision"]["decision"],
            "closed": [(t["symbol"], t["exit_reason"], t["r_multiple"])
                       for t in report["closed_trades"]],
        }

    assert fingerprint(first.stdout) == fingerprint(second.stdout)
