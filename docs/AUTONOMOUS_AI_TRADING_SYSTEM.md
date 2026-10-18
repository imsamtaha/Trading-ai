# ATLAS — Autonomous AI Trading System

## P0: deterministic autonomy governance (Paper only)

ATLAS is **Autonomous AI Trading System**, a bounded, inspectable market-intelligence architecture, not a profit-predicting bot. Risk limits, data quality, stop controls, and evidence provenance have authority over directional analysis. No 80–95% return or unvalidated win probability is claimed.

### Modules in this PR

- `app/intelligence/autonomy_governor.py`: importable, broker-neutral checks for candle validity, decision-quality score, and deterministic fail-closed Paper decision assessment.
- `tests/test_autonomy_governor.py`: synthetic test cases for gap, duplicate, stale, malformed bars and risk vetoes.
- `docs/AUTONOMOUS_AI_TRADING_SYSTEM.md`: implementation and deployment constraints.

### Decision contracts

1. The **data-quality gate** rejects stale/future, missing/duplicate, non-monotonic, inconsistent OHLC and anomalous bid/ask evidence. Pass completed candles with a known interval and explicit quote-spread limit.
2. **Decision Quality** is a transparent 0–110 evidence score; it is *never* a probability of success.
3. An autonomous Paper candidate requires explicit `kill_switch=ACTIVE`; fresh data, healthy API, independently verified portfolio exposure/correlation and four aligned timeframes with risk approval; normal event and volatility conditions; Senior Risk acceptance; complete quality points; and an independently validated calibration profile.
4. Missing or contradictory evidence yields **NO_TRADE**. `DEFENSIVE` and `HALTED` never produce a candidate.
5. All results carry `environment=PAPER`, `broker_execution_allowed=false` and `paper_execution_performed=false`. A `LONG` or `SHORT` return is an **advisory paper candidate**, never permission to send orders.
6. `record_assessment` appends a local JSONL record containing snapshot ID, rationale codes and the non-executable decision.

The current calibration contract checks supplied metadata; it does not independently verify model files or out-of-sample claims. **Never pass untrusted client-supplied evidence into a live execution path.** An owner-controlled evidence validator and held-out test report are required before relying on the probability field.

### Testing

Run, from repository root:

```powershell
$env:ATLAS_LIVE_TRADING = 'false'
$env:ATLAS_DASHBOARD_ONLY = 'true'
python -m pytest -q tests/test_autonomy_governor.py
python -m pytest -q
```

GitHub's pull-request workflow also runs full Python tests on Linux and Windows, plus the public demo checks. A green test run is **not** validation of real market performance.

### Deployment status and limits

**Staged source code only.** Importable functions and tests are committed to a feature branch; the module is **not wired** into the current Windows Paper Monitor, Council, production private API, broker adapter, or public website.

Promotion gates before any integration with a Paper decision:
- Verify actual market-data format, timezone and candle close semantics from the observed feed; avoid gaps caused by known session closures.
- Validate news and economic event timestamps at decision time.
- Recompute portfolio risk, live quote spread and correlations with trusted sources at each candidate decision.
- Run chronological walk-forward and meaningful held-out calibration with costs, slippage and realistic missing data.
- Inject API, stale-feed, spread, portfolio and HALTED faults; verify full decision/audit lineage.
- Reconcile the local Windows runtime's uncommitted changes before deployment; preserve owner-only authentication and read-only public access.

**No auto-merging or public deployment is performed by this PR. Do not enable MT5 order sending.**
