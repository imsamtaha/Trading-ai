# Google Cloud Run Deployment Design

**Date:** 2026-09-13  
**Service:** ATLAS Market public application  
**Repository:** `imsamtaha/Trading-ai`

## Goal

Deploy the existing ATLAS FastAPI application and its static website to Google Cloud Run while preserving the public read-only safety boundary. The deployment must expose `/health`, the website, dashboard, and analysis endpoints without enabling MT5 execution, broker credentials, automatic paper writes, or payment activation.

## Chosen architecture

Cloud Run runs one Linux container built from the repository root. Uvicorn binds to `0.0.0.0` and the Cloud Run-provided `PORT`. The container includes the Python application and `web/` assets. MetaTrader 5 stays on the existing Windows host because the terminal and Python package are Windows-only.

Google Cloud Build builds and pushes the image to Artifact Registry, then deploys it to Cloud Run. The configuration uses the active Google Cloud project through `PROJECT_ID`; it does not hardcode an account or project identifier.

## Runtime safety boundary

The Cloud Run revision receives these immutable deployment settings:

- `ATLAS_LIVE_TRADING=false`
- `ATLAS_DASHBOARD_ONLY=true`
- `ATLAS_AGENT_PAPER_EXECUTION_ENABLED=false`

No `MT5_LOGIN`, `MT5_PASSWORD`, `MT5_SERVER`, API keys, Supabase service keys, or bridge tokens are present in source, the container image, or `cloudbuild.yaml`. Public write routes remain blocked by the application's dashboard-only middleware.

The Cloud Run filesystem is ephemeral. This deployment therefore does not treat local SQLite files, ledgers, or journals as durable evidence. Persistent MT5 demo monitoring and audit records remain on the Windows worker until a separately designed authenticated ingestion path is approved.

## Deployment components

- `Dockerfile`: deterministic Python 3.13 image and Cloud Run-compatible Uvicorn startup.
- `.dockerignore`: excludes Git history, local environments, credentials, runtime data, tests, caches, and generated output.
- `cloudbuild.yaml`: builds, pushes, and deploys `atlas-market` in `europe-west1` using Artifact Registry repository `atlas`.
- `scripts/deploy_google_cloud.ps1`: idempotent Windows operator flow that selects a project, enables required APIs, creates the Artifact Registry repository if absent, submits the build, and verifies `/health`.
- `tests/test_google_cloud_deployment.py`: enforces the port contract, required assets, disabled trading flags, secret exclusions, and health verification.
- `docs/GOOGLE_CLOUD_DEPLOY.md`: exact first deployment, verification, logs, rollback, and custom-domain instructions.

## Public access and domain

The initial Cloud Run service is unauthenticated because it is the public marketing/read-only application. The generated `run.app` URL is verified first. Only after `/health` succeeds should `justai-atlas.online` be mapped and its DNS records changed. Domain mapping is kept out of the automated script so a failed revision cannot replace a working public domain.

## Failure handling

Cloud Build stops on build, push, or deploy failure. The operator script stops on command errors and checks the deployed health endpoint. Cloud Run revisions are immutable, so rollback uses traffic migration to a known-good revision. Runtime logs are read from Cloud Run; no broker or account secrets should appear because they are not configured in this service.

## Acceptance criteria

1. The deployment validation test fails before Google Cloud files exist and passes after they are added.
2. The existing full Python and JavaScript suites remain green in GitHub Actions.
3. The image starts with the Cloud Run `PORT` contract and includes both `app/` and `web/`.
4. Deployed environment settings keep live trading, dashboard writes, and agent paper execution disabled.
5. A real deployment is accepted only after the returned service URL responds to `GET /health` with HTTP 200 and `status=healthy`.
6. No claim is made that Cloud Run connects to MT5, executes demo broker orders, or preserves the Windows audit journal.
