# MT5 delivery safety after PR #70

Execution switches remain unchanged. This patch does not enable trading.

## What the code enforces

- Automatic sizing refuses pending orders anywhere in the account because their
  unfilled exposure is not included in the portfolio risk calculator.
- The coordinator retains a fingerprint of all open positions (symbol, side,
  volume, stop and ticket). The broker refuses delivery if this exposure changed
  after risk approval, including a position on another symbol.
- Immediately before sending an opening order, the broker rechecks positions,
  pending orders and account identity. The configured one-position rule applies
  to opening orders; automatic orders also refuse late pending exposure.
- Opening and closing orders share the thread/process portfolio lock. Closing
  orders validate the connected account and the position again before delivery.
- A SQLite reservation is committed before `order_send`. `SUBMITTING` and
  `UNCERTAIN` block further opening and closing requests on the account, including
  after a crash/restart. No transport error or partial acknowledgement triggers
  an automatic retry. A journal write failure refuses execution.
- Full `DONE` acknowledgements require the requested volume, positive order/deal
  IDs and a finite positive fill price before recording `FILLED`.

## Shared durable storage

The default journal is `~/.atlas/mt5-submissions.sqlite3`, outside the checkout.
All ATLAS processes controlling the same account must use the same persistent
path. Set `ATLAS_MT5_SUBMISSION_DB` to an absolute durable path if the Windows
service account or home directory differs. Protect its permissions and include
it in backups. Do not delete or replace it to bypass an unresolved delivery.
The SQLite file is private runtime data and must not be committed.

## Inspect and reconcile on the Windows worker

```powershell
python scripts/mt5_submission_status.py
python scripts/mt5_submission_status.py --reconcile
```

These commands never submit or close orders and never change execution switches.
The second updates journal evidence only. Exit codes: 0 = no unresolved delivery;
2 = account remains blocked; 3 = evidence/journal/connection unavailable.

Reconciliation clears a reservation only when unique positive deal tickets
belong to one positive order ID and match the exact ATLAS submission comment,
symbol, magic, direction and requested volume. Broker order history must confirm
the exact completed order with no remaining volume. Close evidence uses the
position identifier, which can differ from the current position ticket.

Missing history, altered comments, partial fills, rejected results without full
fill evidence, active remainders and unmatched evidence remain blocked. Absence
of a deal is not proof of non-delivery. There is no automatic resend or blind
reset command. Keep execution off and investigate such cases directly in MT5
and with the broker; manage urgent positions directly in MT5 when necessary.

## Remaining operating boundaries

This is a local coordination mechanism, not an atomic broker transaction. A
human, another EA, or another host can trade after the final read. Run one
designated executor for the account and exclude other writers while automatic
execution is enabled. This patch does not claim a distributed account lock or
exactly-once delivery at the broker.

Pre-send prices and cash risk are estimates. Broker fill slippage, gaps, fees and
stop execution can exceed the estimated budget. Reconciliation proves delivery,
not trade quality or profitability.

Before activation, verify the deployed commit, shared journal path, intended
account identity and execution settings, then validate these boundaries with a
connected FXPro demo terminal. Unit tests simulate MT5; CI does not place trades.
