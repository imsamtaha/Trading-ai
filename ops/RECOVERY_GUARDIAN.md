# ATLAS Recovery Guardian

Recovery Guardian is a veto-only supervisor in the existing Paper decision flow. It never imports a broker, submits orders, selects direction, changes position size, raises risk limits, or resets the daily ledger.

The monitor fits diagnostics only to unique settled outcomes with an explicit PAPER, broker-disabled training intent and a timezone-aware close at or before observation. Invalid provenance or nonfinite data vetoes new entries. Identical duplicates are ignored; conflicting duplicates invalidate the evidence. Future outcomes are excluded.

For each symbol and strategy, the latest 20 outcomes form a descriptive review. A nonpositive mean Paper R quarantines that pair only after at least 10 outcomes spanning 3 UTC calendar days. Calendar-day coverage is not statistical independence. Unseen or undersampled pairs remain eligible for evidence collection subject to all existing strategy, quote, risk and Council gates.

Spread greater than 25% of the candidate stop distance vetoes entry. This is a fixed experimental guard, not a profit prediction. It includes the observed bid/ask spread but does not model fees.

The active Windows startup script sets ATLAS_RECOVERY_AGENT_ENABLED=true and writes an atomic report at .runtime/paper/atlas_recovery_agent.json each completed cycle. The protected owner bridge displays the supervisor separately from directional training accuracy; its HOLD opinion is excluded from directional calibration.

The 7% daily realized-loss cap, 150 daily-entry cap, 10 open-position cap, fresh-quote guard and category concentration cap remain active. The existing supervisor handles stopped Paper tasks with bounded recovery. It samples heartbeat time after probes to avoid classifying a concurrently updated log as stale.

An offline Council fit and chronological calibration run were performed on 196 unique outcomes, with 113 training, 39 validation and 40 holdout examples (4 boundary examples purged). The holdout does not establish profitable strategy selection. Replay output is stored under .runtime/research/intensive-20261011; no records or live weights are multiplied by replaying the same data.
