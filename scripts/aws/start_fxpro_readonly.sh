#!/usr/bin/env bash
# Foreground only; this listener must never be exposed to the public Internet.
set -euo pipefail
umask 077
root="$(cd -- "$(dirname -- "$0")/../.." && pwd -P)"
cd "$root"
venv="$HOME/.local/share/atlas-fxpro/venv"
if [[ ! -x "$venv/bin/python" ]]; then
  echo "ERROR: Run bash scripts/aws/setup_fxpro_readonly.sh first." >&2
  exit 2
fi
require="none"
if [[ -v ATLAS_FXPRO_REQUIRE ]]; then
  require="$ATLAS_FXPRO_REQUIRE"
fi
# Check inherited values BEFORE forcing conservative defaults.
"$venv/bin/python" scripts/aws/fxpro_preflight.py --require "$require"
export ATLAS_LIVE_TRADING=false
export ATLAS_ENVIRONMENT=paper
export ATLAS_DASHBOARD_ONLY=true
export ATLAS_AGENT_PAPER_EXECUTION_ENABLED=false
export ATLAS_AUTO_EXECUTION_ENABLED=false
export ATLAS_REAL_MONEY_EXECUTION=false
export ATLAS_DEMO_ORDER_EXECUTION=false
export ATLAS_USER_REAL_ORDERS=false
export ATLAS_USER_DEMO_ORDERS=false
export ATLAS_MT5_CONNECTIONS_PAUSED=true
export ATLAS_BROKER_PROVIDER=ctrader
port="8766"
if [[ -v ATLAS_FXPRO_STATUS_PORT ]]; then
  port="$ATLAS_FXPRO_STATUS_PORT"
fi
exec "$venv/bin/python" -m uvicorn scripts.atlas_provider_status:app \
  --host 127.0.0.1 --port "$port" --no-access-log
