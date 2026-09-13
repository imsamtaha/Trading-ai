# Deploy ATLAS to Google Cloud Run

This guide deploys the ATLAS website and FastAPI dashboard to Cloud Run. It does **not** move MetaTrader 5, broker credentials, the Windows paper worker, or durable ledgers to Google Cloud.

## Safety boundary

Every deployed revision is forced to:

```text
ATLAS_LIVE_TRADING=false
ATLAS_DASHBOARD_ONLY=true
ATLAS_AGENT_PAPER_EXECUTION_ENABLED=false
ATLAS_PUBLIC_ANALYSIS_ENABLED=false
```

The public service permits read-only pages and API reads. Trading, billing writes, paper writes, and unauthenticated analysis POSTs are blocked. The deployment contains no MT5 credentials, provider API keys, Supabase service key, or connector token.

Cloud Run's filesystem is ephemeral. Do not use its local SQLite files or JSON ledgers as durable trading evidence.

## Deployment model

Cloud Build only builds and pushes an image to Artifact Registry. The authenticated operator script then:

1. refuses to deploy a dirty Git working tree;
2. tags the image with the full Git commit SHA;
3. generates fresh, release-specific runtime and build service accounts and refuses to reuse an existing identity;
4. rejects unexpected project roles on either new identity;
5. grants the build identity only project log writing and repository-scoped Artifact Registry writing;
6. rejects an existing multi-container service and clears inherited secrets, volumes, Cloud SQL, and VPC settings;
7. deploys a tagged candidate revision with no production traffic;
8. retries `GET /health` and verifies `POST /mt5/test-order` returns `403`;
9. moves 100% of traffic to the verified tag and checks the canonical URL again.

The script never changes the active project in the global `gcloud` configuration.

## Prerequisites

1. A Google Cloud project with billing enabled.
2. Google Cloud CLI and Git installed on the Windows computer.
3. The current `Trading-ai` repository checked out with a clean working tree.
4. An authenticated operator allowed to enable services, create Artifact Registry repositories and service accounts, manage the two narrow IAM bindings, submit builds, deploy Cloud Run services, and act as both service accounts.
5. Permission to create two fresh service accounts per release. Their random suffix prevents inherited principal-specific grants; the script stops if either identity already exists or receives an unexpected project binding.

Confirm the CLI:

```powershell
gcloud --version
gcloud auth login
gcloud projects list
git status --short
```

Use the project **ID**, not its display name. Do not grant Owner and do not create or store a service-account key in this repository.

## First deployment

From a clean repository root:

```powershell
.\scripts\deploy_google_cloud.ps1 -ProjectId "YOUR_GOOGLE_CLOUD_PROJECT_ID"
```

Defaults:

| Setting | Value |
| --- | --- |
| Region | `europe-west1` |
| Artifact Registry repository | `atlas` |
| Cloud Run service | `atlas-market` |
| Runtime service account | `atlas-run-RANDOM8@PROJECT_ID.iam.gserviceaccount.com` |
| Build service account | `atlas-build-RANDOM8@PROJECT_ID.iam.gserviceaccount.com` |
| Build permissions | project Logs Writer; repository-scoped Artifact Registry Writer |
| Public access | enabled |
| Minimum / maximum instances | 0 / 3 |
| Memory | 512 MiB |
| Live trading and paper writes | disabled |
| Public analysis POSTs | disabled |

A permission error, existing generated identity, or unexpected IAM role is a stop condition. The script does not grant the runtime identity any role. It grants the fresh build identity only `roles/logging.logWriter` at project level and `roles/artifactregistry.writer` on the selected repository. Old runtime identities must remain while their revisions are rollback candidates; retire old build identities and bindings later through a separately reviewed cleanup.

Redeployment deliberately clears inherited secrets, secret/other volumes and mounts, Cloud SQL connections, Serverless/Direct VPC networking, and network tags. It refuses to modify a service with more than one container so an unreviewed sidecar cannot survive the release.

## Verify the deployed revision

The script prints the canonical service URL, candidate URL, source revision, and runtime identity. You can repeat the checks:

```powershell
$serviceUrl = gcloud run services describe atlas-market --project "YOUR_GOOGLE_CLOUD_PROJECT_ID" --region europe-west1 --format="value(status.url)"
Invoke-RestMethod "$serviceUrl/health"

try {
    Invoke-WebRequest -Method Post "$serviceUrl/mt5/test-order"
} catch {
    [int]$_.Exception.Response.StatusCode
}
```

Expected health payload:

```json
{
  "status": "healthy",
  "service": "atlas-ultimate-api"
}
```

Expected write-route status: `403`. The middleware rejects the request before the endpoint can connect to a broker.

## Logs and rollback

```powershell
gcloud run services logs read atlas-market --project "YOUR_GOOGLE_CLOUD_PROJECT_ID" --region europe-west1 --limit 100
gcloud run revisions list --service atlas-market --project "YOUR_GOOGLE_CLOUD_PROJECT_ID" --region europe-west1
gcloud run services update-traffic atlas-market --project "YOUR_GOOGLE_CLOUD_PROJECT_ID" --region europe-west1 --to-revisions="HEALTHY_REVISION_NAME=100"
```

Use an exact revision name from the list.

## Custom domain after health verification

Do not modify Namecheap DNS until the generated `run.app` URL passes both checks.

Cloud Run direct domain mapping is a preview feature. It is available in `europe-west1`, but Google does not recommend it as the production option. For an initial controlled release:

```powershell
gcloud domains list-user-verified
gcloud domains verify justai-atlas.online
gcloud beta run domain-mappings create --service atlas-market --domain justai-atlas.online --region europe-west1 --project "YOUR_GOOGLE_CLOUD_PROJECT_ID"
gcloud beta run domain-mappings describe --domain justai-atlas.online --region europe-west1 --project "YOUR_GOOGLE_CLOUD_PROJECT_ID"
```

Copy every returned `resourceRecords` entry into Namecheap exactly. Managed certificate provisioning can take several minutes and, in some cases, up to 24 hours. For a durable production edge, use Firebase Hosting or a global external Application Load Balancer in front of Cloud Run.

## What remains on Windows

- MT5 terminal connection and account verification
- broker-exact candles and quotes
- paper/demo worker and heartbeat
- paper ledger and JSONL signal journal
- any future broker-demo or live execution gate

The public Cloud Run service must never receive MT5 login credentials.
