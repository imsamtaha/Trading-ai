# Demo operations and live-review handoff

## Current operating structure

The Windows MT5 terminal supplies account metadata, candles and quotes to the
paper worker. The existing strategy, unified decision and risk gates determine
whether to record a candidate in the local paper ledger. Subsequent quotes
close simulated positions at their stop or target. No broker orders are sent.

```
MT5 demo session -> MT5 candles -> deterministic strategy / decision / risk
                                         -> local paper ledger
MT5 subsequent quotes -------------------> simulated closes -> review metrics
Worker heartbeat + ledger ----------------> read-only dashboard
```

The separate Agent panel evaluates the existing public-provider multi-timeframe
decision endpoint. It is decision support, not the paper worker's execution
policy. Do not combine its confidence or public-provider prices with worker
ledger results in performance reporting. Unifying these two policies and
validating them on the same data is a prerequisite for any live-engine release.

## Start and stop on Windows

Create `.venv`, install `requirements.txt`, and keep the configured MT5 demo
account signed in. Password storage is optional when using the terminal session.
The demo launcher forces demo-account validation and all execution restrictions.

```powershell
.\scripts\start_demo_session.ps1
.\scripts\start_demo_session.ps1 -Stop
```

The dashboard is `http://127.0.0.1:8000/dashboard`. Choose another free port with
`-Port`. The launcher records only the processes it started, refuses duplicate
or partial sessions, and leaves the MT5 terminal and paper ledger intact when
stopping. It runs hidden background processes, not a Windows service. Sleep,
logout or reboot can interrupt it; run the launcher again after signing in.
Do not run another legacy monitor alongside this session against the same ledger.

Use `ATLAS_AUTO_DISCOVER_SYMBOLS=false` and `ATLAS_SYMBOLS=EURUSD` for the initial
operating check. `ATLAS_CYCLE_SECONDS=30` controls the evaluation interval.
There is no requirement to force a trade: `NO_TRADE` is a valid gate outcome.

## Observe and recover

- `/health`: web service health, not MT5 connectivity.
- `/dashboard/state` and `/dashboard/atlas`: read-only broker telemetry aliases.
- `/dashboard/demo-status`: paper summary, worker freshness, review progress.
- `RUNNING`: latest cycle completed without a data/analysis error.
- `DEGRADED`: cycle completed with one or more symbol errors.
- `UNAVAILABLE`: session/account/analysis setup failed; worker retries next cycle.
- `STALE`: the last heartbeat is older than three cycles (minimum 90 seconds).
- `NOT_STARTED`: there is no worker heartbeat yet.

Inspect `data/dashboard-errors.log`, `data/demo-worker-errors.log`,
`data/atlas_demo_status.json`, and `data/atlas_signals.jsonl` locally. Credentials,
runtime records, and logs are not committed. Back up the ledger and journal
before any migration. On account mismatch or loss of demo status, reconnect to
the configured demo session; the launcher does not change accounts or enable
orders. Corrupt status/ledger data reports unavailability, never readiness.

## Live-review release stages

| Stage | Required evidence | Current gate |
|---|---|---|
| Local paper operations | Correct demo account; fresh candles; heartbeat; ledger; tests | Enabled with execution disabled |
| Forward-demo evidence | At least 25 closed trades; positive expectancy; profit factor >= 1.10; drawdown / total risk <= 10% | Existing screening rule only |
| Strategy validation | One frozen policy and dataset; out-of-sample evaluation; costs, spread, slippage and stale-data behavior | Required before live release |
| Broker-demo validation | Contract-aware sizing and min/step/max lots; order acknowledgement, partial fills, rejection, reconciliation, restart/duplicate handling | Not supplied by the paper ledger |
| Operational risk controls | Tested daily-loss and exposure caps; equity drawdown; disconnect/stale-price stop; emergency stop; monitoring and recovery rehearsal | Must be implemented and validated for the live executor |
| Owner release | Review the evidence, account, instruments and risk limits; authorize a specific live deployment | Separate future decision |

Passing the statistical screen produces `REVIEW_REQUIRED`, never live activation.
The drawdown denominator is total recorded risk, not account starting equity.
Paper P&L is simulated and cannot substantiate broker execution or live returns.
Do not label the system live-ready until every applicable release gate has evidence.

## Advertising readiness

Prepare product-demo and early-access messaging now. Use only verified feature
claims: multi-timeframe analysis, explicit WAIT outcomes, deterministic risk
checks, a read-only dashboard and a clearly labelled paper session. Do not use
account numbers, demo balances, fabricated testimonials, win rates or profit
claims in creative. A public destination, confirmed offer, audience, platform
eligibility review and an approved budget are still needed before paid launch.
