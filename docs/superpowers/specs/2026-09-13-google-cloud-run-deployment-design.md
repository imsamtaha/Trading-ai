# Google Cloud Run Deployment Design

**Date:** 2026-09-13  
**Service:** ATLAS Market public application  
**Repository:** `imsamtaha/Trading-ai`

## Goal

Deploy the existing ATLAS FastAPI application and static website to Google Cloud Run as a public read-only surface. The cloud service exposes health, website, dashboard, and read endpoints without enabling MT5 execution, broker credentials, automatic paper writes, billing writes, or unauthenticated analysis POSTs.

## Architecture

Cloud Run runs one Linux container built from the repository root. Uvicorn binds to `0.0.0.0` and the Cloud Run-provided `PORT`. MetaTrader 5 and durable trading evidence stay on the Windows host.

Cloud Build has a build-only role: it builds the image and pushes it to Artifact Registry. The authenticated operator performs the Cloud Run deployment. This avoids giving the build identity Cloud Run deployment or service-account impersonation authority.

Each image is tagged with the full, clean Git commit SHA. The operator creates a tagged Cloud Run candidate with `--no-traffic`, verifies the candidate URL, and only then promotes the verified tag to 100% traffic.

## Runtime identity and safety

Cloud Run uses a dedicated user-managed runtime service account with no project roles. Cloud Build uses a separate user-managed identity with project-level Logs Writer and repository-scoped Artifact Registry Writer only. The script rejects unexpected project roles on either reused identity; the operator must be allowed to act as both.

Every cloud revision receives:

- `ATLAS_LIVE_TRADING=false`
- `ATLAS_DASHBOARD_ONLY=true`
- `ATLAS_AGENT_PAPER_EXECUTION_ENABLED=false`
- `ATLAS_PUBLIC_ANALYSIS_ENABLED=false`

No MT5 credentials, provider keys, Supabase service keys, or bridge tokens enter source, the image, or build configuration. Public writes and potentially costly unauthenticated analysis POSTs are rejected by middleware. Redeployment clears inherited secrets, volumes and mounts, Cloud SQL connections, and VPC settings, and refuses an existing multi-container service.

The Cloud Run filesystem is ephemeral. SQLite files, ledgers, and journals inside it are not durable evidence.

## Components

- `Dockerfile`: Python 3.13 container, non-root runtime, Cloud Run port contract.
- `.dockerignore`: excludes credentials, runtime evidence, local state, tests, and generated output.
- `cloudbuild.yaml`: build and push only under an explicit `_BUILD_SERVICE_ACCOUNT`; image tag is `_SOURCE_REVISION`.
- `scripts/deploy_google_cloud.ps1`: validates a clean source revision, provisions minimal runtime identity, performs staged deployment, verifies health and the write guard, then promotes traffic.
- `tests/test_google_cloud_deployment.py`: enforces build, identity, traceability, staging, safety, retry, and CI contracts.
- `docs/GOOGLE_CLOUD_DEPLOY.md`: operator prerequisites, deployment, verification, rollback, and deferred domain mapping.

## Public access and domain

The service is unauthenticated because it is the public marketing/read-only application. The generated `run.app` URL is verified first. DNS changes remain outside automation and require the exact Google-generated records after runtime verification.

## Failure handling

Build or deployment errors stop the script. Candidate failures receive no production traffic. Health checks retry with bounded delay. A candidate is rejected unless its health payload reports `healthy` and its execution test route returns `403`. Cloud Run revisions are immutable, so rollback moves traffic to a known-good revision.

## Acceptance criteria

1. Full Python, JavaScript, Docker smoke, and PowerShell parse checks pass in CI.
2. The image starts with the Cloud Run `PORT` contract and contains `app/` and `web/`.
3. Build identity does not deploy Cloud Run.
4. Runtime and build use separate dedicated identities; unexpected project roles stop deployment.
5. Existing secrets, storage/database/network attachments, and extra containers cannot be inherited silently.
6. Image and service labels trace to the full Git commit SHA.
7. Candidate deployment receives no traffic before health and `403` safety verification.
8. Trading, paper writes, and public analysis POSTs are disabled in Cloud Run.
9. No claim is made that Cloud Run connects to MT5 or preserves the Windows audit journal.
