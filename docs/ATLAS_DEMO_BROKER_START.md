# Broker demo execution and dashboard activity

The dashboard's Refresh All now refreshes account telemetry, markets/news,
analysis/risk, the chart, simulated demo telemetry and setup scanning. Analysis
also refreshes after changing its market or timeframe. Navigation includes
analysis/risk, chart, chat and setup sections. Chat remains a user-triggered
conversation; refresh does not send a chat message. Unavailable providers continue
to show unavailable states rather than invented activity.

Risk labels and result states switch between Arabic and English with the saved
language setting and remain localized after dynamic updates.

## Requested demo limits

- Maximum 15 ATLAS broker demo entries per Beirut calendar day.
- Maximum 5 total currently open positions on the demo account before a new entry.
- Existing stop-loss, portfolio loss/open-risk limits, account identity checks,
  one-position-per-symbol restriction and uncertain-delivery blocking remain.
- These are ceilings, not a target or an instruction to force 15 trades.

Daily ATLAS entries are reserved transactionally in the persistent submission
journal. Filled and uncertain/submitting entry reservations count; cancelled
before-send reservations and closing orders do not. Positions closed during the
day still consume the daily entry budget. Manual or other-system entries are not
included in the journal's daily ATLAS count. All local workers must share the
same submission database and portfolio lock. Independent hosts/terminals do not
gain distributed atomic isolation from this change.

Environment overrides:

```dotenv
ATLAS_DEMO_MAX_DAILY_ENTRIES=15
ATLAS_DEMO_MAX_OPEN_POSITIONS=5
```

## Windows start, after verifying the active FXPro demo account

```powershell
.\ATLAS_SWITCH.ps1 -Mode DEMO_TRADE -DailyTrades 15 -OpenPositions 5 -Symbol EURUSD
```

`DEMO` retains its existing simulated/read-only broker behavior. `DEMO_TRADE`
requires an active demo terminal, pins `MT5_REQUIRE_DEMO=true`, and starts the
automatic worker with `--demo-only`. The worker refuses a non-demo account before
analysis; the broker also rechecks account identity before delivery. The legacy
`ATLAS_LIVE_TRADING=true` setting in this mode means broker delivery is enabled,
not that a real-money account is permitted.

The analytical provider must supply a valid fresh `ATLAS_AUTO_CONTEXT_FILE`.
Missing context, missing quotes/history or rejected risk blocks entries; this
launcher does not fabricate evidence to make trading start. One symbol is scanned
by this launcher and existing duplicate-symbol rules apply. A five-position ceiling
does not promise that five different symbols will be scanned or traded.

Check `/runtime/status`, `/dashboard/atlas`, worker output, and the persistent
submission journal against MT5 demo history before calling execution active.
`BROKER_DEMO_CONFIGURED` on the dashboard describes configuration, not confirmed
worker activity or fills. Simulated demo statistics remain separate from broker
positions/history.

Stop broker execution with:

```powershell
.\ATLAS_SWITCH.ps1 -Mode OFF
```

Deployment and live FXPro verification cannot be performed while the Windows
device is offline. No remote account or runtime was activated by creating this patch.
