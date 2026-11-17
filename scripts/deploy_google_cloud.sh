#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${1:-}"
PROJECT_NUMBER="${ATLAS_GCP_PROJECT_NUMBER:-}"
REGION="${ATLAS_GCP_REGION:-europe-west1}"
SERVICE="${ATLAS_GCP_SERVICE:-atlas-market}"
REPOSITORY="${ATLAS_GCP_REPOSITORY:-atlas}"

if [[ -z "$PROJECT_ID" ]]; then
  if [[ -n "$PROJECT_NUMBER" ]]; then
    PROJECT_ID="$(gcloud projects list --filter="projectNumber=$PROJECT_NUMBER" --format="value(projectId)" | head -n1)"
  else
    PROJECT_ID="$(gcloud config get-value project 2>/dev/null || true)"
  fi
fi

if [[ -z "$PROJECT_ID" || "$PROJECT_ID" == "(unset)" ]]; then
  echo "ERROR: No Google Cloud project selected."
  echo "Usage: ATLAS_GCP_PROJECT_NUMBER=245439987004 ./scripts/deploy_google_cloud.sh"
  echo "   or: ./scripts/deploy_google_cloud.sh YOUR_PROJECT_ID"
  exit 1
fi

for cmd in gcloud git curl python3; do
  command -v "$cmd" >/dev/null 2>&1 || { echo "ERROR: $cmd is required."; exit 1; }
done

ACTIVE_ACCOUNT="$(gcloud auth list --filter='status:ACTIVE' --format='value(account)' | head -n1)"
if [[ -z "$ACTIVE_ACCOUNT" ]]; then
  echo "ERROR: No active Google Cloud account. Run: gcloud auth login"
  exit 1
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if [[ -n "$(git status --porcelain)" ]]; then
  echo "ERROR: Git working tree is not clean. Commit or stash changes before deployment."
  exit 1
fi

SOURCE_REVISION="$(git rev-parse HEAD | tr '[:upper:]' '[:lower:]')"
if [[ ! "$SOURCE_REVISION" =~ ^[0-9a-f]{40}$ ]]; then
  echo "ERROR: Unable to resolve full Git source revision."
  exit 1
fi

echo "Using Google Cloud account: $ACTIVE_ACCOUNT"
echo "Project: $PROJECT_ID"
echo "Source revision: $SOURCE_REVISION"

gcloud config set project "$PROJECT_ID" >/dev/null

gcloud services enable   artifactregistry.googleapis.com   cloudbuild.googleapis.com   iam.googleapis.com   run.googleapis.com   cloudresourcemanager.googleapis.com   --project "$PROJECT_ID"

if ! gcloud artifacts repositories describe "$REPOSITORY"     --location "$REGION"     --project "$PROJECT_ID" >/dev/null 2>&1; then
  gcloud artifacts repositories create "$REPOSITORY"     --repository-format docker     --location "$REGION"     --description "ATLAS Cloud Run images"     --project "$PROJECT_ID"     --quiet
fi

SUFFIX="$(python3 - <<'PY'
import secrets
print(secrets.token_hex(4))
PY
)"
RUNTIME_SA="atlas-run-$SUFFIX"
BUILD_SA="atlas-build-$SUFFIX"
RUNTIME_IDENTITY="$RUNTIME_SA@$PROJECT_ID.iam.gserviceaccount.com"
BUILD_IDENTITY="$BUILD_SA@$PROJECT_ID.iam.gserviceaccount.com"
BUILD_RESOURCE="projects/$PROJECT_ID/serviceAccounts/$BUILD_IDENTITY"

gcloud iam service-accounts create "$RUNTIME_SA"   --display-name "ATLAS Cloud Run runtime"   --description "Runtime-only identity for ATLAS Cloud Run release $SOURCE_REVISION"   --project "$PROJECT_ID"   --quiet

gcloud iam service-accounts create "$BUILD_SA"   --display-name "ATLAS Cloud Build worker"   --description "Build-only identity for ATLAS release $SOURCE_REVISION"   --project "$PROJECT_ID"   --quiet

gcloud projects add-iam-policy-binding "$PROJECT_ID"   --member "serviceAccount:$BUILD_IDENTITY"   --role "roles/logging.logWriter"   --condition=None   --quiet >/dev/null

gcloud artifacts repositories add-iam-policy-binding "$REPOSITORY"   --location "$REGION"   --project "$PROJECT_ID"   --member "serviceAccount:$BUILD_IDENTITY"   --role "roles/artifactregistry.writer"   --condition=None   --quiet >/dev/null

if gcloud run services describe "$SERVICE"     --region "$REGION"     --project "$PROJECT_ID"     --format=json >/tmp/atlas-service.json 2>/dev/null; then
  CONTAINER_COUNT="$(python3 - <<'PY'
import json
with open('/tmp/atlas-service.json', encoding='utf-8') as f:
    data = json.load(f)
containers = (((data.get('spec') or {}).get('template') or {}).get('spec') or {}).get('containers') or []
print(len(containers))
PY
)"
  if [[ "$CONTAINER_COUNT" -gt 1 ]]; then
    echo "ERROR: Existing Cloud Run service has more than one container. Refusing to modify it."
    exit 1
  fi
fi

IMAGE_URI="$REGION-docker.pkg.dev/$PROJECT_ID/$REPOSITORY/$SERVICE:$SOURCE_REVISION"

gcloud builds submit   --config cloudbuild.yaml   --region "$REGION"   --project "$PROJECT_ID"   --service-account "$BUILD_RESOURCE"   --substitutions "_REGION=$REGION,_REPOSITORY=$REPOSITORY,_SERVICE=$SERVICE,_SOURCE_REVISION=$SOURCE_REVISION,_BUILD_SERVICE_ACCOUNT=$BUILD_SA"   .

CANDIDATE_TAG="candidate-${SOURCE_REVISION:0:12}"

gcloud run deploy "$SERVICE"   --image "$IMAGE_URI"   --region "$REGION"   --project "$PROJECT_ID"   --platform managed   --allow-unauthenticated   --ingress all   --port 8080   --cpu 1   --memory 512Mi   --concurrency 40   --min-instances 0   --max-instances 3   --timeout 60   --service-account "$RUNTIME_IDENTITY"   --no-traffic   --tag "$CANDIDATE_TAG"   --clear-secrets   --clear-volumes   --clear-volume-mounts   --clear-cloudsql-instances   --clear-vpc-connector   --set-env-vars "ATLAS_LIVE_TRADING=false,ATLAS_DASHBOARD_ONLY=true,ATLAS_AGENT_PAPER_EXECUTION_ENABLED=false,ATLAS_PUBLIC_ANALYSIS_ENABLED=false,ATLAS_WHISH_ENABLED=true,ATLAS_WHISH_RECIPIENT=76420910,ATLAS_WHISH_SUPPORT=info@justai-atlas.online"   --labels "source-revision=$SOURCE_REVISION,managed-by=atlas-deploy-script"   --quiet

SERVICE_JSON="$(gcloud run services describe "$SERVICE"   --region "$REGION"   --project "$PROJECT_ID"   --format=json)"

CANDIDATE_URL="$(CANDIDATE_TAG="$CANDIDATE_TAG" SERVICE_JSON="$SERVICE_JSON" python3 - <<'PY'
import json, os
data = json.loads(os.environ['SERVICE_JSON'])
tag = os.environ['CANDIDATE_TAG']
for item in ((data.get('status') or {}).get('traffic') or []):
    if item.get('tag') == tag and item.get('url'):
        print(item['url'])
        break
PY
)"

if [[ ! "$CANDIDATE_URL" =~ ^https:// ]]; then
  echo "ERROR: Could not resolve candidate URL."
  exit 1
fi

healthy=0
for attempt in {1..10}; do
  if curl -fsS "$CANDIDATE_URL/health" | python3 -c 'import json,sys; d=json.load(sys.stdin); raise SystemExit(0 if d.get("status")=="healthy" else 1)' 2>/dev/null; then
    healthy=1
    break
  fi
  sleep "$(( attempt < 5 ? attempt : 5 ))"
done

if [[ "$healthy" -ne 1 ]]; then
  echo "ERROR: Candidate health check failed: $CANDIDATE_URL/health"
  exit 1
fi

STATUS_CODE="$(curl -sS -o /dev/null -w '%{http_code}' -X POST "$CANDIDATE_URL/mt5/test-order")"
if [[ "$STATUS_CODE" != "403" ]]; then
  echo "ERROR: Safety check failed. POST /mt5/test-order returned $STATUS_CODE, expected 403."
  exit 1
fi

gcloud run services update-traffic "$SERVICE"   --region "$REGION"   --project "$PROJECT_ID"   --to-tags "$CANDIDATE_TAG=100"   --quiet

SERVICE_URL="$(gcloud run services describe "$SERVICE"   --region "$REGION"   --project "$PROJECT_ID"   --format='value(status.url)')"

curl -fsS "$SERVICE_URL/health" | python3 -m json.tool

echo
echo "ATLAS Cloud Run deployment is healthy."
echo "Service:          $SERVICE_URL"
echo "Candidate:        $CANDIDATE_URL"
echo "Health:           $SERVICE_URL/health"
echo "Source revision:  $SOURCE_REVISION"
echo "Runtime identity: $RUNTIME_IDENTITY"
echo "Build identity:   $BUILD_IDENTITY"
echo "Mode:             public read-only; trading, paper writes, and public analysis POSTs disabled"
