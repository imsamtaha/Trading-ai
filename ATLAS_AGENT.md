# ATLAS Agent v1 — Paper Decision Agent

ATLAS Agent v1 is a paper-only orchestration layer built on top of the existing deterministic ATLAS market, technical, structure, signal, trade-candidate, and risk engines.

## Safety boundary

- The agent does not call MT5 execution routes.
- `ATLAS_LIVE_TRADING` is not used by the agent.
- Paper execution is disabled by default.
- To enable simulated paper writes, set `ATLAS_AGENT_PAPER_EXECUTION_ENABLED=true`.
- Every paper execution request must also send `confirmed=true` and contain a risk-approved `TRADE_CANDIDATE`.

## API

### Capabilities

`GET /agent/capabilities`

Returns available tools and confirms `mode=paper_only` and `live_execution=false`.

### Decision

`POST /agent/decision`

Example body:

```json
{
  "symbol": "XAUUSD",
  "interval": "1h",
  "limit": 100,
  "account_balance": 10000,
  "risk_percent": 1
}
```

The result includes technical analysis, structure, signal, trade candidate, deterministic risk result, selected skills, rationale, and a final decision of `WAIT` or `PAPER_CANDIDATE`.

### Multi-timeframe decision

Use the same read-only endpoint with `multi_timeframe=true`:

```json
{
  "symbol": "EURUSD",
  "multi_timeframe": true,
  "limit": 120,
  "account_balance": 10000,
  "risk_percent": 1
}
```

The fixed set is `5m`, `15m`, `30m`, and `1h`; `interval` is ignored in this
mode and `limit` applies to each frame. Each runs the existing deterministic
analysis, signal, trade-candidate, and risk engines using the requested account
balance and risk percentage. No LLM or new signal/risk scoring is introduced.

- `PAPER_CANDIDATE` requires all four actionable signals to agree on `LONG` or
  `SHORT`, matching candidate directions, and approval from every risk evaluation.
- A neutral signal, conflicting direction, rejected candidate/risk, or failed or
  invalid analysis vetoes the aggregate to `WAIT`. There is no majority fallback.
- On approval, the candidate entry/stop/target are the unchanged `5m` engine
  levels, with its freshly evaluated risk. Aggregate confidence is the minimum
  of the four signal confidences; it is not a calibrated probability.
- On `WAIT`, aggregate confidence is zero, aggregate risk is unapproved, and the
  aggregate trade contains no executable levels. Per-frame results remain visible.

The response has `interval="multi"`, `timeframe_decisions` keyed by the four
intervals (including technical, structure, signal, trade, risk, and rationale),
and `candidate_interval="5m"` on approval or `null` on WAIT. Top-level technical,
structure, and approved signal fields describe the 5m anchor; use
`timeframe_decisions` for the other frames. Failed frames have `status="UNAVAILABLE"`.
Provider failures return an explainable WAIT response, without provider error details.

This is a conservative orchestration policy, not a backtested strategy. Data is
fetched sequentially using the existing providers, not as an atomic snapshot;
the existing candle freshness and open-candle behavior are unchanged. A slow
provider can take up to its existing timeout for each of the four requests.

The dashboard defaults to **All: 5m + 15m + 30m + 1h**, shows per-frame decisions,
confidence, risk and rationale, and retains single-frame selection. Omitting
`multi_timeframe` keeps the previous single-frame API behavior. Neither mode
executes a paper order or calls MT5, even when paper execution is enabled.

Validate with the same command as `.github/workflows/tests.yml`:

```sh
ATLAS_LIVE_TRADING=false ATLAS_DASHBOARD_ONLY=true python -m pytest -q
```

Keep `ATLAS_AGENT_PAPER_EXECUTION_ENABLED=false` for normal decision-only use.

### Paper execution

`POST /agent/paper/execute`

This route is intentionally blocked by dashboard-only mode and requires the opt-in environment flag plus explicit confirmation.

## Skills

The first ATLAS skill set is stored in `atlas-skills/`:

- market-analysis
- technical-analysis
- market-structure
- risk-management
- trade-review

The skills guide orchestration and explanation. They never override deterministic engine outputs.
