# ATLAS Council v3: research implementation

This implements the measuring-stick phase of the Edge-First design. It does not replace the running Council, train or promote a production model, start a worker, or authorize orders. The existing Council → Senior Risk → Executive → PAPER path remains authoritative.

## Implemented and remaining

| Area | Current implementation | Still required |
|---|---|---|
| Data | Strict chronological OHLC, availability timestamps, hashed feature snapshots | Audited point-in-time vendor history, corporate actions and venue coverage |
| Alpha | Deterministic trend, mean-reversion and breakout hypotheses | Independent OOS evidence and portfolio ablation |
| Labels/costs | Non-overlapping next-bar triple barriers; stop-first ambiguous bars; gap losses; explicit round-trip spread/slippage/fees | Real fill calibration, latency, depth and partial fills |
| Meta-labeling | Training-fold frequency buckets, purged chronological folds, calibration and baseline gates | Production model, challenger/champion improvement and drift validation |
| Evidence | Paired cash/trend/seeded-random/v2.1 comparisons; block bootstrap lower bounds; declared-trial correction; 1/1.5/2× costs | Matched portfolio risk-adjusted performance, broader testing correction and independent review |
| Gate/sizing | Pure research EV/uncertainty gate and bounded Kelly/volatility/drawdown calculations | Validated inputs and integration through existing risk and execution safeguards |
| Registry | Separate local challengers, idempotent writes, no promotion | Verified running champion, decay monitor, shadow and staged promotion |
| News | Strict timestamped structured event validation; no direction authority | Independent source verification and OOS feature ablation |
| UI/bot | Owner evidence panel and read-only bilingual bot status | Deployment on the actual host and fresh report connection |

Statistical regime modeling, decorrelated allocation, Rescue exit training, live adaptation and automated retraining are not implemented by this phase. API-supplied probabilities are caller assertions, not trained or independently attested predictions. All outputs remain RESEARCH_ONLY; no broker adapter is imported.

## Run an offline evaluation

Use one symbol/timeframe per CSV, strictly increasing timezone-aware bar **close** times. Required columns:

```csv
time,available_at,open,high,low,close,spread_bps,slippage_bps,fee_bps
```

All three cost fields are round-trip totals in basis points. `available_at` must reflect when the observation actually became usable; future information is rejected. Do not fabricate zero costs. Labels use next-bar open and a fixed ATR-based stop. OHLC cannot resolve intrabar ordering: both barriers touched means stop first when the open is between barriers. An opening gap beyond the target fills conservatively at the target. This is a conservative prototype fill model, not execution evidence.

```bash
python scripts/evaluate_atlas_v3.py \
  --csv /private/data/instrument.csv \
  --data-kind historical --source-label 'vendor / instrument / timeframe / extraction version' \
  --sleeve trend --horizon 10 --folds 3 --trials 1 \
  --v2-baseline /private/data/v2-decisions.json \
  --output data/atlas_edge_v3_report.json \
  --registry data/atlas_edge_v3_registry.json
```

Declare every attempted configuration, including unsuccessful attempts (`--trials` currently accepts 1–10). Larger searches require a separately designed evaluation protocol. The v2 baseline maps timezone-aware ISO decision timestamps (matched by UTC instant, including equivalent `Z` and offset forms) to saved sides `-1`, `0`, or `1`; missing observations reject the comparison, rather than inventing a flat baseline. At least 200 OOS decision slots are required; expect several thousand bars with the default non-overlapping horizon. Decision slots include abstentions and are not executed trades.

The last 20% of bars is not evaluated by this run. Repeated researcher inspection or reuse of a holdout is outside the tool's ability to attest. Dataset hashes include the full supplied input for provenance. Synthetic inputs are explicitly marked and always rejected for promotion. A successful research card means SHADOW_REVIEW_REQUIRED, never production permission. STC-04 and STC-09 remain pending until actual independent reviews occur. A bootstrap lower bound is an estimate, not a bounded financial worst case.

Metrics are R per fixed decision, not portfolio returns. Annualized Sharpe/Sortino/Calmar are not inferred without an equity/time/risk series. Accuracy alone never establishes profitability. Meta-labeling also checks the training-fold majority baseline, a 52.5% accuracy floor, stability ≥0.8 and ECE ≤0.1; production champion improvement remains unverified.

## Expose evidence

Set `ATLAS_EDGE_V3_REPORT` to the private report path on the API host. No raw ledger is served. The root compatibility API provides `GET /agent/v3/policy`, `GET /agent/v3/status` and a non-executing `POST /agent/v3/evaluate`. The current private API provides owner-only `GET /api/runtime/edge-v3`; the owner runtime page opens evidence on request. Reports older than 24 hours are marked stale. A locally supplied report is never represented as independently attested worker performance.

The bot can use `ATLAS_EDGE_V3_STATUS_URL` pointing to the sanitized HTTPS status endpoint. Do not put owner credentials in a URL or expose private API tokens to consumers. Without a configured endpoint/report the command correctly reports UNAVAILABLE.

## Activation evidence still needed

Before any shadow or live promotion: establish the instrument/timeframe and source history; run the matched baselines and ablations; obtain independent reviews; verify unique settled PAPER outcomes, current worker heartbeat and active profile on the actual host. Existing safety gates and staged deployment must remain in force. These files do not verify the v2.1 gateway is installed on any host.

No Supabase schema was changed. No Bigdata runtime feed, Canva integration or Sites deployment is established by this commit. Bigdata may supply timestamped research context after an actual integration; it must not substitute for executable prices. The existing Sites audience and dashboard were left intact. Private reports must stay outside public repositories and public Sites.
