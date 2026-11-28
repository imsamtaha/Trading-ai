"""Pure offline regression tests for the AWS FxPro read-only bootstrap."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
AWS = ROOT / "scripts" / "aws"
FLAGS = (
    "ATLAS_LIVE_TRADING",
    "ATLAS_ENVIRONMENT",
    "ATLAS_DASHBOARD_ONLY",
    "ATLAS_AGENT_PAPER_EXECUTION_ENABLED",
    "ATLAS_AUTO_EXECUTION_ENABLED",
    "ATLAS_REAL_MONEY_EXECUTION",
    "ATLAS_DEMO_ORDER_EXECUTION",
    "ATLAS_USER_REAL_ORDERS",
    "ATLAS_USER_DEMO_ORDERS",
    "ATLAS_MT5_CONNECTIONS_PAUSED",
)
SECRETS = (
    "ATLAS_CTRADER_DEMO_LOGIN",
    "ATLAS_CTRADER_CLIENT_ID",
    "ATLAS_CTRADER_CLIENT_SECRET",
    "ATLAS_CTRADER_ACCESS_TOKEN",
    "ATLAS_PROVIDER_STATUS_TOKEN",
    "ATLAS_CTRADER_LIVE_LOGIN",
    "ATLAS_CTRADER_LIVE_CLIENT_ID",
    "ATLAS_CTRADER_LIVE_CLIENT_SECRET",
    "ATLAS_CTRADER_LIVE_ACCESS_TOKEN",
    "ATLAS_PROVIDER_LIVE_STATUS_TOKEN",
    "ATLAS_FXPRO_STATUS_PORT",
)

def run_preflight(*args, **updates):
    env = os.environ.copy()
    for key in FLAGS + SECRETS:
        env.pop(key, None)
    env.update(updates)
    return subprocess.run(
        [sys.executable, str(AWS / "fxpro_preflight.py"), *args],
        cwd=ROOT, env=env, text=True, capture_output=True, check=False,
    )

def test_empty_profiles_are_safe_but_not_connected():
    result = run_preflight()
    assert result.returncode == 0
    assert "NOT CONFIGURED" in result.stdout
    assert "Preflight: PASS" in result.stdout

def test_requiring_demo_blocks_unconfigured():
    result = run_preflight("--require", "demo")
    assert result.returncode == 1
    assert "Preflight: BLOCKED" in result.stdout

@pytest.mark.parametrize("key,value", [
    ("ATLAS_LIVE_TRADING", "true"),
    ("ATLAS_ENVIRONMENT", "live"),
    ("ATLAS_DASHBOARD_ONLY", "false"),
    ("ATLAS_AGENT_PAPER_EXECUTION_ENABLED", "true"),
    ("ATLAS_USER_REAL_ORDERS", "true"),
    ("ATLAS_MT5_CONNECTIONS_PAUSED", "false"),
])
def test_unsafe_execution_setting_blocks(key, value):
    result = run_preflight(**{key: value})
    assert result.returncode == 1
    assert key in result.stdout

def test_partial_live_credentials_are_rejected_without_leaking_data():
    result = run_preflight(ATLAS_CTRADER_LIVE_ACCESS_TOKEN="private-token-value")
    assert result.returncode == 1
    assert "LIVE view-only profile is PARTIAL" in result.stdout
    assert "private-token-value" not in result.stdout

def test_reused_demo_and_live_tokens_are_rejected():
    common = "long-independent-secret-token-123456"
    result = run_preflight(
        ATLAS_CTRADER_DEMO_LOGIN="12345678",
        ATLAS_CTRADER_CLIENT_ID="demo-id",
        ATLAS_CTRADER_CLIENT_SECRET="demo-secret",
        ATLAS_CTRADER_ACCESS_TOKEN="demo-oauth",
        ATLAS_PROVIDER_STATUS_TOKEN=common,
        ATLAS_CTRADER_LIVE_LOGIN="87654321",
        ATLAS_CTRADER_LIVE_CLIENT_ID="live-id",
        ATLAS_CTRADER_LIVE_CLIENT_SECRET="live-secret",
        ATLAS_CTRADER_LIVE_ACCESS_TOKEN="live-oauth",
        ATLAS_PROVIDER_LIVE_STATUS_TOKEN=common,
    )
    assert result.returncode == 1
    assert "must be different" in result.stdout
    assert common not in result.stdout

def test_bad_port_fails_closed():
    assert run_preflight(ATLAS_FXPRO_STATUS_PORT="0").returncode == 1
    assert run_preflight(ATLAS_FXPRO_STATUS_PORT="not-a-port").returncode == 1

@pytest.mark.skipif(shutil.which("bash") is None, reason="bash not available")
def test_startup_scripts_parse_as_bash():
    for script in ("setup_fxpro_readonly.sh", "start_fxpro_readonly.sh"):
        result = subprocess.run(
            ["bash", "-n", str(AWS / script)], capture_output=True, text=True,
        )
        assert result.returncode == 0, result.stderr

def test_startup_is_loopback_only_and_read_only():
    script = (AWS / "start_fxpro_readonly.sh").read_text()
    assert "--host 127.0.0.1" in script
    assert "--host 0.0.0.0" not in script
    assert "ATLAS_LIVE_TRADING=false" in script
    assert "ATLAS_AGENT_PAPER_EXECUTION_ENABLED=false" in script
    assert "--no-access-log" in script
    assert "order_send(" not in script
    assert "place_stock_order(" not in script

def test_health_check_fails_closed_when_unconfigured():
    env = os.environ.copy()
    env.pop("ATLAS_PROVIDER_STATUS_TOKEN", None)
    env.pop("ATLAS_PROVIDER_LIVE_STATUS_TOKEN", None)
    result = subprocess.run(
        [sys.executable, str(AWS / "check_fxpro_readonly.py"), "--mode", "both"],
        cwd=ROOT, env=env, capture_output=True, text=True,
    )
    assert result.returncode == 1
    assert "NOT CONFIGURED" in result.stdout
