# ATLAS: 100 daily paper entries and diversified shadow training

User authorization: 2026-10-08, 22:39 Beirut; restore Python confirmed at 22:42.

## Operational behavior
- Scheduled Paper Monitor sets daily entry ceiling to 100; the ledger accepts ceilings 1..100. Default for callers without an explicit setting remains 50.
- Existing entries count toward the ceiling; no ledger reset, no forced daily quota. Existing day boundary remains UTC (03:00 Beirut during summer time).
- Maximum concurrent positions remains 5. Maximum concurrent CRYPTO positions is 2 and STOCKS positions is 2. Other existing daily-loss, aggregate-risk, per-trade-risk and reward/risk gates remain active.
- Monitor scans up to 30 available supported instruments per cycle. Categories take turns filling the list; preferences no longer remove other categories.
- Broker names BITCOIN, ETHEREUM, SOLANA, XRP and other verified aliases map to canonical symbols. A bounded equity registry includes AAPL, TSLA, MSFT, NVDA, AMZN, GOOGL, META, AMD, NFLX, JPM and others.
- Broker discovery may subscribe supported crypto/equity quotes to Market Watch. Subscription is not order submission. Unavailable or stale quotes do not become eligible through this change.
- MT5 orders remain disabled; accounting is simulated risk-normalized paper P&L, not actual broker P&L.

## Training architecture
Existing Council calibration remains enabled and updates trained agent weights only from settled paper outcomes. The existing Node training accelerator is preserved without edits.

A separate L2 logistic entry/abstention selector is enabled in SHADOW mode:
1. Read settled positions from the paper ledger; reject invalid, future-dated, non-paper and broker-enabled outcomes; ignore repeated IDs.
2. Require at least 100 settled unique examples across at least 3 UTC entry dates. These are operational minimums, not proof of accuracy.
3. Use only pre-entry confidence, direction, UTC session hour, strategy and asset category. Outcome, exit and P&L fields never enter the feature vector.
4. Split by entry time: 60% development, 20% calibration, 20% exploratory test. Purge development trades closing at/after calibration start and calibration trades closing at/after test start. Require both label classes and sufficient remaining records.
5. Fit regularized logistic regression on development; fit a logistic calibration mapping on calibration data. Test data never fits either model.
6. Report coverage, Brier, selected/baseline total R, selected profit factor and drawdown in R. The label is positive observed paper R, which includes bid/ask spread but excludes broker fees, funding and commissions.
7. Record timestamped entry/abstain recommendations for all strategy candidates before existing entry gates. Unknown symbol/strategy combinations abstain without a probability.
8. Retrain after each new settled count. SHADOW predictions never change Council decisions, risk approval, portfolio limits or trade entries.

Files: app/intelligence/shadow_selector.py and monitor integration.
Runtime outputs: .runtime/paper/atlas_shadow_report.json and atlas_shadow_predictions.jsonl.

An 80% threshold is an experimental recommendation threshold, not an established success rate. Historical data already inspected makes retrospective reports exploratory. Repeated candidate records and replay passes are not new independent samples. Rejected candidates have no counterfactual outcomes and are not labeled as wins/losses. New asset classes need their own observations before a selector can predict them.

Future automatic promotion to an execution gate is deliberately absent. A separate forward assessment must establish performance after costs and acceptable risk before a reviewed promotion.

## Runtime recovery and deployment
The original Python 3.13.15 executable was missing while already-loaded processes remained alive. Restored the same CPython version using uv's managed distribution, and backed up .venv/pyvenv.cfg before pointing it to the restored installation. Verified MT5 and NumPy imports.
Managed base: AppData/Roaming/uv/python/cpython-3.13.15-windows-x86_64-none.
Do not point this environment at Python 3.14.

Deployment: verify tests, create a locked paper snapshot, set a short supervisor maintenance TTL, restart only Paper Monitor, verify fresh output, release maintenance. Frontend/backend remain running. Keep existing source changes from other tasks untouched.

A bounded six-attempt atomic ledger replace retry handles transient PermissionError sharing locks (maximum sleep 0.62 seconds). Persistent failures still raise; the original ledger stays intact.

Rollback: restore changed tracked files from .runtime/changes-100-shadow-20261008, disable shadow/expanded discovery flags, return launcher cap to 50, restart Paper Monitor. Do not roll back settled data or discard new positions. Keep repaired Python installed.

## Acceptance checks
- 100 entries accepted; the 101st refused; 5 concurrent positions retained.
- Diverse supported categories survive preferred filtering.
- Broker crypto aliases and exchange-suffixed equities recognized.
- Crypto concentration refuses a third open crypto position.
- Shadow abstention cannot alter a paper entry and cannot invoke orders.
- Outcome fields cannot affect features; overlapping labels purged.
- Transient replace locks recover without duplicate trades; persistent failures preserve original bytes.
