from pathlib import Path
import re

import yaml


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_dockerfile_uses_cloud_run_port_and_copies_public_runtime():
    dockerfile = read("Dockerfile")

    assert "python:3.13-slim" in dockerfile
    assert re.search(r"COPY(?: --chown=\S+)? app ./app", dockerfile)
    assert re.search(r"COPY(?: --chown=\S+)? web ./web", dockerfile)
    assert re.search(r"\$\{PORT:-8080\}", dockerfile)
    assert "0.0.0.0" in dockerfile


def test_cloud_deployment_forces_read_only_non_execution_mode():
    config = yaml.safe_load(read("cloudbuild.yaml"))
    script = read("scripts/deploy_google_cloud.ps1")
    rendered = f"{config}\n{script}"

    assert "ATLAS_LIVE_TRADING=false" in rendered
    assert "ATLAS_DASHBOARD_ONLY=true" in rendered
    assert "ATLAS_AGENT_PAPER_EXECUTION_ENABLED=false" in rendered
    assert "--allow-unauthenticated" in rendered
    assert "/health" in script


def test_deployment_files_do_not_embed_private_credentials():
    deployment = "\n".join(
        [
            read("Dockerfile"),
            read("cloudbuild.yaml"),
            read("scripts/deploy_google_cloud.ps1"),
        ]
    )
    forbidden = [
        "MT5_PASSWORD=",
        "MT5_LOGIN=",
        "SUPABASE_SERVICE_ROLE_KEY=",
        "ATLAS_TOOL_BRIDGE_TOKEN=",
    ]

    assert not any(value in deployment for value in forbidden)


def test_dockerignore_excludes_secrets_and_runtime_evidence():
    ignored = set(read(".dockerignore").splitlines())

    assert {".env", ".env.*", "data/", "*.sqlite3"} <= ignored


def test_operator_uses_dedicated_runtime_identity_and_candidate_rollout():
    cloudbuild = yaml.safe_load(read("cloudbuild.yaml"))
    script = read("scripts/deploy_google_cloud.ps1")

    assert not any(step.get("entrypoint") == "gcloud" for step in cloudbuild["steps"])
    assert "--service-account" in script
    assert "--no-traffic" in script
    assert "--tag" in script
    assert "--to-tags" in script


def test_operator_requires_clean_traceable_source_revision():
    cloudbuild = read("cloudbuild.yaml")
    script = read("scripts/deploy_google_cloud.ps1")

    assert "_SOURCE_REVISION" in cloudbuild
    assert "git status --porcelain" in script
    assert "git rev-parse HEAD" in script
    assert "--labels" in script
    assert "source-revision" in script


def test_public_cloud_revision_disables_expensive_analysis_posts():
    script = read("scripts/deploy_google_cloud.ps1")

    assert "ATLAS_PUBLIC_ANALYSIS_ENABLED=false" in script


def test_operator_retries_health_and_checks_write_boundary():
    script = read("scripts/deploy_google_cloud.ps1")

    assert "Start-Sleep" in script
    assert "/mt5/test-order" in script
    assert "StatusCode" in script
    assert "403" in script


def test_ci_parses_powershell_and_checks_container_write_boundary():
    workflow = read(".github/workflows/tests.yml")

    assert "Parse Google Cloud deployment script" in workflow
    assert "http://127.0.0.1:8080/mt5/test-order" in workflow
    assert "403" in workflow


def test_build_uses_dedicated_least_privileged_identity():
    cloudbuild = read("cloudbuild.yaml")
    script = read("scripts/deploy_google_cloud.ps1")

    assert "serviceAccount:" in cloudbuild
    assert "_BUILD_SERVICE_ACCOUNT" in cloudbuild
    assert "BuildServiceAccount" in script
    assert "--service-account" in script
    assert "roles/artifactregistry.writer" in script
    assert "roles/logging.logWriter" in script
    assert "Unexpected project IAM roles" in script


def test_redeployment_clears_inherited_sensitive_infrastructure():
    script = read("scripts/deploy_google_cloud.ps1")

    assert "--clear-secrets" in script
    assert "--clear-volumes" in script
    assert "--clear-volume-mounts" in script
    assert "--clear-cloudsql-instances" in script
    assert "--clear-vpc-connector" in script
    assert "--clear-network" in script
    assert "more than one container" in script


def test_operator_refuses_to_reuse_cloud_service_accounts():
    script = read("scripts/deploy_google_cloud.ps1")

    assert "[Guid]::NewGuid" in script
    assert "Refusing to reuse existing service account" in script
