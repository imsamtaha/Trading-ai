# Google Cloud Run Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make ATLAS deployable to Google Cloud Run as a public, dashboard-only FastAPI service and provide a verified Windows deployment path.

**Architecture:** Build one Linux container from the repository root and deploy it through Cloud Build to Cloud Run. Keep MT5 and persistent demo evidence on the Windows host; force the cloud service into read-only dashboard mode and verify its health endpoint before domain mapping.

**Tech Stack:** Python 3.13, FastAPI, Uvicorn, Docker, Google Cloud Build, Artifact Registry, Cloud Run, PowerShell, pytest

**Spec:** `docs/superpowers/specs/2026-09-13-google-cloud-run-deployment-design.md`

## Global Constraints

- Keep `ATLAS_LIVE_TRADING=false`.
- Keep `ATLAS_DASHBOARD_ONLY=true`.
- Keep `ATLAS_AGENT_PAPER_EXECUTION_ENABLED=false`.
- Do not place MT5 credentials, provider keys, Supabase service keys, or bridge tokens in source or build configuration.
- Do not represent Cloud Run as an MT5 worker or durable audit store.
- Verify the generated `run.app` URL before mapping `justai-atlas.online`.
- Do not change DNS automatically.

---

### Task 1: Define deployability and safety checks

**Files:**
- Create: `tests/test_google_cloud_deployment.py`

**Interfaces:**
- Consumes: repository-root deployment files as UTF-8 text.
- Produces: pytest assertions defining the Cloud Run port, content, safety, secret-exclusion, and health-verification contracts.

- [ ] **Step 1: Write the failing tests**

Create tests that require:

```python
from pathlib import Path
import re
import yaml

ROOT = Path(__file__).resolve().parents[1]

def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")

def test_dockerfile_uses_cloud_run_port_and_copies_public_runtime():
    dockerfile = read("Dockerfile")
    assert "python:3.13-slim" in dockerfile
    assert "COPY app ./app" in dockerfile
    assert "COPY web ./web" in dockerfile
    assert re.search(r"\$\{PORT:-8080\}", dockerfile)
    assert "0.0.0.0" in dockerfile

def test_cloudbuild_forces_read_only_non_execution_mode():
    config = yaml.safe_load(read("cloudbuild.yaml"))
    rendered = str(config)
    assert "ATLAS_LIVE_TRADING=false" in rendered
    assert "ATLAS_DASHBOARD_ONLY=true" in rendered
    assert "ATLAS_AGENT_PAPER_EXECUTION_ENABLED=false" in rendered
    assert "--allow-unauthenticated" in rendered
    assert "/health" in read("scripts/deploy_google_cloud.ps1")

def test_deployment_files_do_not_embed_private_credentials():
    deployment = "\n".join([
        read("Dockerfile"),
        read("cloudbuild.yaml"),
        read("scripts/deploy_google_cloud.ps1"),
    ])
    forbidden = ["MT5_PASSWORD=", "MT5_LOGIN=", "SUPABASE_SERVICE_ROLE_KEY=", "ATLAS_TOOL_BRIDGE_TOKEN="]
    assert not any(value in deployment for value in forbidden)

def test_dockerignore_excludes_secrets_and_runtime_evidence():
    ignored = set(read(".dockerignore").splitlines())
    assert {".env", ".env.*", "data/", "*.sqlite3"} <= ignored
```

- [ ] **Step 2: Run RED**

Run: `python -m pytest tests/test_google_cloud_deployment.py -q`

Expected: FAIL because `Dockerfile`, `.dockerignore`, `cloudbuild.yaml`, and the deployment script do not exist.

- [ ] **Step 3: Commit the RED test**

```bash
git add tests/test_google_cloud_deployment.py
git commit -m "test: define safe Google Cloud deployment"
```

### Task 2: Add the Cloud Run container and build pipeline

**Files:**
- Create: `Dockerfile`
- Create: `.dockerignore`
- Create: `cloudbuild.yaml`

**Interfaces:**
- Consumes: `requirements.txt`, `app/`, and `web/`.
- Produces: image `${_REGION}-docker.pkg.dev/${PROJECT_ID}/${_REPOSITORY}/${_SERVICE}:${COMMIT_SHA}` and Cloud Run service `${_SERVICE}`.

- [ ] **Step 1: Add the minimal Dockerfile**

Use Python 3.13 slim, install `requirements.txt`, copy `app/` and `web/`, run as a non-root user, and start Uvicorn on `${PORT:-8080}`.

- [ ] **Step 2: Add the build-context exclusions**

Exclude Git state, local virtual environments, environment files, runtime data, SQLite databases, caches, tests, generated output, and editor metadata.

- [ ] **Step 3: Add Cloud Build**

Build and push the Artifact Registry image, then deploy to managed Cloud Run in `europe-west1` with unauthenticated access, port 8080, conservative autoscaling, and all three safety flags explicitly disabled/enabled as required.

- [ ] **Step 4: Run focused tests**

Run: `python -m pytest tests/test_google_cloud_deployment.py -q`

Expected: the Dockerfile and ignore checks pass; the missing deployment script check still fails.

- [ ] **Step 5: Commit container and build files**

```bash
git add Dockerfile .dockerignore cloudbuild.yaml
git commit -m "feat: add safe Cloud Run build"
```

### Task 3: Add operator deployment and verification

**Files:**
- Create: `scripts/deploy_google_cloud.ps1`
- Create: `docs/GOOGLE_CLOUD_DEPLOY.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: a Google Cloud project ID supplied as `-ProjectId`.
- Produces: enabled APIs, Artifact Registry repository `atlas`, submitted Cloud Build, Cloud Run service URL, and a validated `/health` response.

- [ ] **Step 1: Implement the PowerShell deployment script**

The script must:

1. require `-ProjectId`;
2. default `-Region` to `europe-west1`;
3. select the project;
4. enable Cloud Build, Cloud Run, Artifact Registry, and Resource Manager APIs;
5. create the Artifact Registry repository only when absent;
6. submit `cloudbuild.yaml` with explicit substitutions;
7. query the deployed service URL;
8. call `GET /health`;
9. stop unless HTTP 200 and JSON `status` equals `healthy`.

- [ ] **Step 2: Document first deployment and operations**

Document prerequisites, exact PowerShell invocation, safety boundary, health verification, log reading, revision listing, rollback, and deferred custom-domain mapping.

- [ ] **Step 3: Link the guide from README**

Add a concise Google Cloud section that points to `docs/GOOGLE_CLOUD_DEPLOY.md` and states that Cloud Run does not host MT5.

- [ ] **Step 4: Run GREEN**

Run:

```bash
python -m pytest tests/test_google_cloud_deployment.py -q
python -m pytest -q
node --test tests/test_demo_model.cjs
node --test tests/test_google_auth.mjs
python scripts/build_website.py
```

Expected: all checks pass.

- [ ] **Step 5: Commit operator flow**

```bash
git add scripts/deploy_google_cloud.ps1 docs/GOOGLE_CLOUD_DEPLOY.md README.md
git commit -m "docs: add verified Google Cloud deployment flow"
```

### Task 4: Validate through GitHub and deploy

**Files:**
- No source changes expected.

**Interfaces:**
- Consumes: branch CI and the operator's authenticated Google Cloud project.
- Produces: passing CI evidence and a live Cloud Run URL whose `/health` returns HTTP 200.

- [ ] **Step 1: Open a pull request and inspect every workflow job**

Do not merge while any required test is failing.

- [ ] **Step 2: Merge after CI passes**

Use the repository's normal merge flow. Preserve any unrelated open branches and PRs.

- [ ] **Step 3: Run the authenticated deployment**

From Windows PowerShell:

```powershell
.\scripts\deploy_google_cloud.ps1 -ProjectId "<your-google-cloud-project-id>"
```

The angle-bracket value is operator input, not stored configuration.

- [ ] **Step 4: Verify the live service**

Accept only a printed HTTPS Cloud Run URL and a health payload with `status: healthy`.

- [ ] **Step 5: Defer DNS until runtime verification**

Map `justai-atlas.online` only after the run.app URL is healthy. DNS changes require the exact Google-generated records and remain a separate explicitly approved operation.
