# Agent Performance XGBoost

Purpose: rank customer-support agents using sale probability and predicted CSAT.
This is advisory routing telemetry. It does not set council trading weights, route
broker orders, or establish profitable trading performance.

## Changes

- Fixed the incomplete sample feature values and used stable caller-supplied IDs.
- One aligned 60/20/20 train/validation/test split; early stopping uses validation,
  reported metrics use the untouched test split.
- Observed data uses chronological splits. Supply aggregates known before each
  outcome to avoid leakage. Historical CSAT must exclude the scored interaction.
- Scores stay within 0..1. CSAT is clipped to its 1..5 domain and normalized with
  (CSAT - 1) / 4 rather than training-prediction minimum and maximum.
- Feature schema, target alignment, finite values, weights, and counts are validated.
- Each model uses one CPU thread. Training runs offline, outside API requests.
- Native XGBoost JSON models and metadata are saved in a single atomic ZIP bundle.
  Checksums and metadata are validated before publishing a replacement.
- A failed save preserves the old bundle; a failed API reload keeps the last
  successfully loaded model and reports DEGRADED.
- No pickle/joblib deserialization is used.

## Install and train

Use the existing ATLAS virtual environment:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-agent-performance.txt
.\.venv\Scripts\python.exe train_agent_performance.py --demo
.\.venv\Scripts\python.exe train_agent_performance.py --csv observed-interactions.csv
```

CSV columns: agent_experience_months, avg_handle_time_mins, historical_csat,
total_chats_handled, current_workload, sale_success, csat_outcome, occurred_at.
Use at least 50 rows, both sale classes in each split, and unique UTC event
timestamps. CSAT outcomes must be 1..5; sale outcomes must be 0 or 1.

Demo training writes .runtime/models/agent_performance_demo.bundle.zip.
Observed training writes .runtime/models/agent_performance.bundle.zip.
ATLAS_AGENT_PERFORMANCE_MODEL can override the prefix. Models are local runtime
artifacts and are not committed. Production readiness remains false until an
independent deployment decision grounded in real observed outcomes.

## API

Owner authentication is required for both endpoints. Responses are private/no-store.

- GET /api/runtime/agent-performance/status
- POST /api/runtime/agent-performance/scores

Scores accept agents (1..100 records with unique agent_id and the five features),
w_sales, w_csat, and allow_synthetic. Synthetic scoring requires the explicit
allow_synthetic=true flag and is marked DEMO_READY. No training happens on request.
Missing models return UNTRAINED/503; corrupt updates report DEGRADED.

## Paper process recovery

The Paper launcher runs the worker through ops/rotate_paper_logs.py --run instead
of a PowerShell native-command pipeline. The Python runner streams stdout and
stderr directly, takes a single-writer lock, returns the worker's exit code, and
keeps an active log capped at 16MiB plus three rotated logs. The pre-existing large
log is retained as an archive on first rotation. Ledger and trading flags remain
outside this change. A wrapper launcher and its child Python process are one
worker, not two independent workers.

Shadow and Recovery report writes now reuse the already verified Windows ReplaceFileW fallback when normal replacement is denied. Shadow temporary files are unique, flushed, and cleaned. Live verification confirmed both reports refresh with new generated_at timestamps.

