# ATLAS Trader View, Filters, and Drawdown Alerts Design

## Goal
Extend the existing ATLAS demo Performance Center with three read-only capabilities: performance filters by asset and timeframe, drawdown alerting based on paper-trading evidence, and a public-safe trader view that exposes only aggregated demo statistics.

## Scope
This change is limited to the existing paper-demo analytics and website/dashboard presentation. It must not enable broker order submission, live execution, subscriber execution, or automatic promotion from demo to live.

## Architecture
The existing `app/dashboard/demo_panel.py` remains the source of demo analytics. Its performance helper will be extended so it can calculate metrics for an optional symbol and timeframe while preserving the current aggregate response. A dedicated alert summary will be derived from existing readiness drawdown evidence and the paper equity curve.

A new read-only public endpoint will expose a reduced `trader_view` payload that omits account credentials, provider errors, raw broker telemetry, internal readiness reasoning, and any order-capable control. The browser panel will add local filter controls and render filtered data from the same read-only endpoint.

## Data model
`performance` will keep its existing aggregate keys and add:
- `available_assets`: sorted symbols present in closed demo trades.
- `available_timeframes`: sorted timeframe labels present in closed demo trades.
- `filtered`: metrics for the requested asset/timeframe selection.
- `selection`: normalized active filters.

`alerts` will contain:
- `level`: `NORMAL`, `WATCH`, or `HIGH`.
- `drawdown_percent`: current readiness drawdown percentage.
- `message`: short human-readable risk message.
- `live_activation_blocked`: always `true` in this demo subsystem.

`/dashboard/trader-view` will expose only:
- mode/status summary.
- closed/open trade counts.
- aggregate/filtered performance metrics needed for display.
- drawdown alert level and message.
- explicit `paper_demo: true` and `broker_orders: false` flags.

## Filter semantics
- Missing or `ALL` asset means all symbols.
- Missing or `ALL` timeframe means all timeframes.
- Matching is case-insensitive.
- Unknown filters return an empty metric set, not an error.
- The filtered metric basis remains `risk_normalized_pnl`; it must never be labelled broker P&L.

## Drawdown alert semantics
Use the readiness field `max_drawdown_percent_of_total_risk` as the authoritative drawdown input.
- `< 20%`: `NORMAL`.
- `20%` to `< 35%`: `WATCH`.
- `>= 35%`: `HIGH`.

These thresholds are monitoring signals only and do not alter trading behavior.

## UI
The Performance Center will add two selects (`Asset`, `Timeframe`) and update the win rate, cumulative risk-normalized P/L, equity curve, best/worst asset, and trade history for the selection without enabling any execution control.

A visible Drawdown Alert badge will show the current level and message. The public trader view will use the same aggregate style but omit internal events and readiness details.

## Safety boundaries
- `automatic_live_activation` remains `false`.
- No MT5 order endpoint is called or exposed.
- No account login, server, balance, equity, credentials, or raw provider errors are returned by the trader-view endpoint.
- P/L is always identified as risk-normalized paper performance.

## Testing
Tests must prove:
1. filters return correct per-symbol and per-timeframe metrics;
2. unknown filters produce zero/empty metrics safely;
3. drawdown alert thresholds map correctly;
4. public trader view omits sensitive/internal fields and explicitly blocks broker execution semantics;
5. dashboard script contains filter controls and drawdown alert UI;
6. existing demo safety tests remain green;
7. full Python and public website validation CI passes.
