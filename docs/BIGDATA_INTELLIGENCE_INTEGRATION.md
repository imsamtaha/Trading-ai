# Bigdata.com → ATLAS INTELLIGENCE

## Status
Initial read-only ingestion adapter added. This is **not** a live Bigdata API integration, authenticated feed, dashboard deployment, or proof of live market data. API access and the production backend contract must be verified before enabling automated ingestion.

## Supported research inputs
Bigdata.com search can provide sourced financial news, filings, transcripts and research. Market tearsheets, company sentiment and economic calendars can supply additional context through separately authorized integration workflows.

Use `app/intelligence/bigdata_research.py` to normalize sourced research records with a title, HTTPS source URL and timezone-aware publication timestamp. Each record retains provenance and freshness metadata.

## Safety
- The adapter is read-only and has no broker imports, secrets, network calls or MT5 permissions.
- Every item is tagged `research_only=true`, `paper_only=true`, `broker_execution_allowed=false` and `signal_action=HOLD`.
- Missing provenance, malformed timestamps and future-dated sources fail closed.
- Items older than 24 hours are flagged stale. Stale research must not be promoted to an actionable signal.
- No news item should directly modify Council weights, Paper ledgers or agent outcomes. Any downstream inference must pass the existing Council → Senior Risk → Executive → PAPER pipeline.
- Preserve `ATLAS_LIVE_TRADING=false` and existing permissions.

## Proposed next phase (not implemented)
1. Confirm the authorized Bigdata API entitlement and backend authentication mechanism; keep credentials server-side.
2. Implement scheduled retrieval with rate limits, deduplication, caching, source attribution and health monitoring.
3. Add a protected dashboard panel showing source links, timestamps, stale/error states and separate facts from model interpretation.
4. Validate Arabic RTL and Android layouts, permissions, API error handling and paper-only end-to-end tests.
5. Deploy to the original service only after CI, owner authorization and verification.

Run: `python -m pytest -q tests/test_bigdata_research.py`.
