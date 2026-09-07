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
