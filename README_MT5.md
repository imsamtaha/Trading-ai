# ATLAS MT5 Forward-Demo Worker

## Architecture

ATLAS runs its decision logic in Python. A persistent Windows worker owns the
MetaTrader 5 terminal connection. During forward-demo validation, it never
sends an MT5 order. Instead, it opens qualified candidates in a local paper
ledger, evaluates them using subsequent MT5 quotes, and stores every material
open/close/error event in Supabase when credentials are available.

`ATLAS -> Scoring/Risk Gate -> Paper Ledger -> MT5 Quotes`

`MT5 Worker -> local JSONL + Supabase audit events`

## Windows setup

1. Install MetaTrader 5 and log into a **demo** account.
2. Clone this repository on the same Windows machine where MT5 is installed.
3. Create `.env` from `.env.mt5.example`.
4. Set `MT5_TERMINAL_PATH`, `MT5_LOGIN`, `MT5_PASSWORD`, and `MT5_SERVER`.
5. Set `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` to the project values. Never commit `.env` or that key.
6. Install dependencies: `python -m pip install -r requirements.txt`.
7. Verify the terminal connection: `python scripts/verify_mt5.py`.
8. Run one safe connected cycle: `python run_atlas_mt5.py --once`.
9. Start continuous forward-demo registration: `python run_atlas_mt5.py`.
10. Inspect progress at any time: `python scripts/atlas_demo_status.py`.

The PowerShell shortcut is:

```powershell
.\scripts\start_atlas_demo.ps1
```

## Recorded trade lifecycle

- `PAPER_TRADE_OPENED`: strategy, unified decision, and risk gates all approved an entry.
- `PAPER_TRADE_CLOSED`: an MT5 quote touched the paper position's stop loss or take profit.
- `NO_TRADE` and `SKIPPED`: kept in the local signal journal; optional Supabase persistence is enabled with `ATLAS_PERSIST_ALL_SIGNALS=true`.
- `MT5_ERROR` / `ERROR`: persisted for diagnosis.

The durable local records are `data/atlas_demo_ledger.json` and
`data/atlas_signals.jsonl`. Supabase material events are written to
`public.atlas_execution_events`.

## Safety

`ATLAS_LIVE_TRADING=false` is mandatory for this runner. If it is changed to
`true`, the runner exits before connecting. The worker uses MT5 only for
account metadata, symbols, and quotes; it does not invoke the MT5 order API.

A paper ledger is not a broker fill record and its P&L is explicitly
risk-normalized. It is appropriate for validating signal quality and process,
not for claiming live trading performance.

## Live-review gate

The status report requires at least 25 **closed** paper trades, positive
expectancy, profit factor of at least 1.10, and drawdown within the configured
limit. Passing these checks produces `REVIEW_REQUIRED`; it never enables live
trading automatically. Live execution also requires out-of-sample validation,
MT5 lot-size conversion tests, order reconciliation, daily-loss limits, and a
manual owner approval.
