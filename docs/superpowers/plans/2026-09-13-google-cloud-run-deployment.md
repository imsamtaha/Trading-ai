# Google Cloud Run Deployment Implementation Plan

> **Execution skill:** `superpowers:executing-plans`

**Goal:** Make ATLAS deployable to Google Cloud Run as a public, read-only FastAPI service with a verified Windows operator path.

**Architecture:** Cloud Build builds and pushes a source-addressed container. A logged-in operator deploys a no-traffic candidate to Cloud Run under a dedicated runtime identity, verifies health and the execution guard, then promotes traffic. MT5 and persistent evidence remain on Windows.

**Spec:** `docs/superpowers/specs/2026-09-13-google-cloud-run-deployment-design.md`

## Safety constraints

- `ATLAS_LIVE_TRADING=false`
- `ATLAS_DASHBOARD_ONLY=true`
- `ATLAS_AGENT_PAPER_EXECUTION_ENABLED=false`
- `ATLAS_PUBLIC_ANALYSIS_ENABLED=false`
- no credentials or service-account keys in source/build configuration
- no automated DNS change
- no production traffic before candidate health and `403` verification

## Task 1: Define deployment contracts

- [x] Add failing tests for container, build, secrets, and safety flags.
- [x] Capture the expected RED CI result.
- [x] Add tests for dedicated runtime identity, staged rollout, source traceability, retry behavior, and write-boundary verification.
- [x] Capture the hardened RED CI result.

## Task 2: Add the container and build-only pipeline

- [x] Add a non-root Python 3.13 `Dockerfile` using the Cloud Run port contract.
- [x] Add `.dockerignore` exclusions for secrets and runtime evidence.
- [x] Add `cloudbuild.yaml` that builds and pushes an image tagged by full source revision.
- [x] Keep Cloud Run deployment authority out of the Cloud Build steps.

## Task 3: Add staged operator deployment

- [x] Require a clean Git tree and resolve the full commit SHA.
- [x] Enable required APIs and create Artifact Registry only when absent.
- [x] Create or reuse a dedicated runtime service account without granting it project roles.
- [x] Build the exact source revision.
- [x] Deploy a tagged candidate with `--no-traffic`.
- [x] Retry candidate `/health` and require `POST /mt5/test-order` to return `403`.
- [x] Promote only the verified tag to 100% traffic.
- [x] Recheck the canonical service URL.
- [x] Avoid changing the operator's active `gcloud` project.

## Task 4: Document and validate

- [x] Document IAM boundaries, first deployment, verification, logs, rollback, and deferred custom-domain mapping.
- [x] Link the staged deployment from README.
- [x] Add Linux Docker health/write smoke checks.
- [x] Add a Windows PowerShell parser check.
- [ ] Obtain a green final GitHub Actions run.
- [ ] Obtain final code-review approval.

## Task 5: Release and authenticated deployment

- [ ] Merge through the repository's normal flow after all checks and review pass.
- [ ] Run the script from an authenticated Windows checkout with the user's Google Cloud project ID.
- [ ] Record the printed HTTPS URL and verify the live health payload.
- [ ] Keep DNS deferred until the `run.app` URL passes runtime checks.

The final two deployment steps require an authenticated Google Cloud project and cannot be simulated by repository CI.
