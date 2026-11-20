# ATLAS Training Accelerator v2

The tool evaluates agent confidence calibration on settled PAPER outcomes. It does not place orders or promote experimental weights into the operational Council profile.

## Running
Windows from ATLAS:
```powershell
node scripts/atlas_training_accelerator.mjs
node --test tests/test_training_accelerator.mjs
```
The scheduled Paper Monitor now invokes it at startup and whenever the settled-trade count changes, when ATLAS_TRAINING_ACCELERATOR_ENABLED=true. The call has a 15-second timeout; failure is logged without changing trading decisions. Runtime is independent of the replay report.

CLI: --journal, --ledger, --output-dir, --min-improvement (default0.01), --min-days (default3), --min-validation (default20).
A custom journal without --ledger is marked as lacking verified entry times. The default run uses the operational journal and paper ledger read-only.

## Evaluation
1. Reject malformed, future, live/broker-enabled and conflicting records; ignore exact duplicate snapshots.
2. Join each journal snapshot to its settled ledger trade. Validate label, entry/settlement timing and paper execution flags.
3. Order by entry time; split 60% development /20% validation /20% retrospective test. Purge development positions still open at validation start and validation positions still open at test start.
4. Optimize one bounded confidence multiplier per trained agent (0.50..1.50) on development only. The baseline uses the existing Council reliability formula, calculated from development only.
5. Consider hypothetical acceptance only with 3 entry dates, at least20 validation samples per agent and Brier improvement>=0.01. These are operational gates, not proof of statistical independence or80% accuracy.
6. Show accuracy with descriptive Wilson95% intervals, confidence calibration bins, high-confidence development errors, symbol/strategy/date coverage and risk-normalized paper R.
7. Freeze exact source snapshots with SHA256 and save an immutable report for each run, plus latest-report.json. Historical tests have been viewed before; repeated runs do not provide fresh independent validation.

Outputs: .runtime/research/training-accelerator/.
No writes into the operational PAPER directory or its descendants, including resolved symbolic paths.

## What confidence weighting means
A proposed multiplier scales reported confidence; it does not supply an independent BUY/SELL signal. On the current76 examples, both trained agents agree on every direction. Better calibration therefore does not establish better direction selection or a higher trade win rate.
The live Council profile and retrospective baseline refer to different sample windows. Do not compare their weights as if they were the same model.

The separate Python entry/abstention selector runs in SHADOW mode. It requires100 settled examples across3 entry dates, uses pre-entry features and purged chronological splits, and logs observations without changing entry gates. Its0.8 threshold is experimental, not an achieved80% success rate.

## Verified first v2 replay, 2026-10-08
76 unique settled outcomes across2 entry dates:
- Development41; validation13; retrospective test16.
- Purged4 development and2 validation outcomes.
- Both agents: SHADOW_DEFERRED_DATA (insufficient dates and validation count).
- Technical candidate0.50 improved validation Brier0.38678 ->0.27894.
- Confidence candidate0.50 worsened validation Brier0.28268 ->0.28912.
- No proposed weights deployed.

## Operational limits
The monitor allows up to100 qualified paper entries per UTC day (03:00 Beirut in summer); it does not force100 trades. Maximum5 concurrent positions, maximum2 CRYPTO and2 STOCKS positions, existing loss/risk gates remain active. Category ceilings are checked within the cross-process ledger lock. Discovery samples up to30 supported broker instruments, and scan order rotates to reduce position-slot bias toward the same first symbols.

Broker names and market availability matter: the new mapping includes BITCOIN/ETHEREUM/SOLANA and exchange-suffixed equities such as AAPL.O/TSLA.O. Unsupported, unavailable or stale assets do not receive fabricated quotes or labels.

## File locking incident
A partial-read stream in Desktop Commander held the operational ledger open without allowing atomic replacement on Windows. Confirmed the exact read-only holder, released that reader and verified locked atomic persistence. Do not partially read active runtime files through file-preview tools; inspect a copied snapshot or a short-lived terminal read instead. Transient sharing locks receive bounded retries; persistent failures remain explicit errors. No data was discarded.

## Remaining limitations
Samples across dates can still be correlated. Executed trades are selected by the existing strategy; rejected candidates lack counterfactual labels. Paper R includes bid/ask effects but excludes commissions, funding and real broker execution. Unusual gap exits are retained, not cosmetically clipped. A replay cannot certify future returns.
