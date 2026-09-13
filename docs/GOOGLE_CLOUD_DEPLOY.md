# Deploy ATLAS to Google Cloud Run

This guide deploys the ATLAS website and FastAPI dashboard to Cloud Run. It does **not** move MetaTrader 5, broker credentials, the Windows paper worker, or durable ledgers to Google Cloud.

## Safety boundary

Every deployed revision is forced to:

```text
ATLAS_LIVE_TRADING=false
ATLAS_DASHBOARD_ONLY=true
ATLAS_AGENT_PAPER_EXECUTION_ENABLED=false
```

The deployment contains no MT5 credentials, provider API keys, Supabase service key, or connector token. Cloud Run's filesystem is ephemeral; do not use its local SQLite files or JSON ledgers as durable trading evidence.

## Prerequisites

1. A Google Cloud project with billing enabled.
2. Google Cloud CLI installed on the Windows computer.
3. Permission to enable APIs, submit Cloud Builds, write to Artifact Registry, deploy Cloud Run services, and make the public website unauthenticated.
4. The current `Trading-ai` repository checked out locally.

Confirm the CLI:

```powershell
gcloud --version
gcloud auth login
gcloud projects list
```

Use the project **ID**, not its display name, in the deployment command.

## First deployment

From the repository root:

```powershell
.\scripts\deploy_google_cloud.ps1 -ProjectId "YOUR_GOOGLE_CLOUD_PROJECT_ID"
```

Defaults:

| Setting | Value |
| --- | --- |
| Region | `europe-west1` |
| Artifact Registry repository | `atlas` |
| Cloud Run service | `atlas-market` |
| Public access | enabled |
| Minimum instances | 0 |
| Maximum instances | 3 |
| Memory | 512 MiB |
| Live trading | disabled |
| Dashboard-only guard | enabled |
| Agent paper execution writes | disabled |

The script enables the required APIs, creates the Docker repository when needed, submits `cloudbuild.yaml`, obtains the service URL, and calls `GET /health`. It succeeds only when the returned JSON contains `"status": "healthy"`.

If Cloud Build reports an IAM error, grant only the role named in the error to the build service account, then rerun the same script. Do not grant Owner and do not place a service-account key in this repository.

## Verify the deployed revision

```powershell
$serviceUrl = gcloud run services describe atlas-market --region europe-west1 --format="value(status.url)"
Invoke-RestMethod "$serviceUrl/health"
Start-Process "$serviceUrl/"
```

Expected health response:

```json
{
  "status": "healthy",
  "service": "atlas-ultimate-api"
}
```

Also verify that a write route stays blocked:

```powershell
try {
    Invoke-WebRequest -Method Post "$serviceUrl/mt5/test-order"
} catch {
    $_.Exception.Response.StatusCode.value__
}
```

Expected status: `403`. This check does not submit a broker order because the dashboard-only middleware rejects the request before the endpoint runs.

## Logs and revisions

Read recent application logs:

```powershell
gcloud run services logs read atlas-market --region europe-west1 --limit 100
```

List immutable revisions:

```powershell
gcloud run revisions list --service atlas-market --region europe-west1
```

Move all traffic back to a known healthy revision:

```powershell
gcloud run services update-traffic atlas-market --region europe-west1 --to-revisions="HEALTHY_REVISION_NAME=100"
```

Use an exact revision name returned by the preceding list command.

## Custom domain after health verification

Do not modify Namecheap DNS until the generated `run.app` URL passes the health and write-block checks.

Cloud Run direct domain mapping is currently a preview feature. Google supports it in `europe-west1`, but does not recommend it for production latency. For an initial controlled release, verify domain ownership and create the mapping:

```powershell
gcloud domains list-user-verified
gcloud domains verify justai-atlas.online
gcloud beta run domain-mappings create --service atlas-market --domain justai-atlas.online --region europe-west1
gcloud beta run domain-mappings describe --domain justai-atlas.online --region europe-west1
```

Copy every `resourceRecords` entry from the final command into Namecheap exactly. The managed certificate can take from several minutes up to 24 hours. For the durable production setup, put Firebase Hosting or a global external Application Load Balancer in front of Cloud Run instead of relying on preview domain mapping.

## What remains on Windows

The following processes stay on the persistent Windows/MT5 host:

- MT5 terminal connection and account verification
- broker-exact candles and quotes
- paper/demo worker
- heartbeat
- paper ledger and JSONL signal journal
- any future broker-demo or live execution gate

The public Cloud Run service must never receive MT5 login credentials.
