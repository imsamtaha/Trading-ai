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


def test_cloudbuild_forces_read_only_non_execution_mode():
    config = yaml.safe_load(read("cloudbuild.yaml"))
    rendered = str(config)

    assert "ATLAS_LIVE_TRADING=false" in rendered
    assert "ATLAS_DASHBOARD_ONLY=true" in rendered
    assert "ATLAS_AGENT_PAPER_EXECUTION_ENABLED=false" in rendered
    assert "--allow-unauthenticated" in rendered
    assert "/health" in read("scripts/deploy_google_cloud.ps1")


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
