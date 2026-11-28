#!/usr/bin/env bash
# Install only status-reader dependencies; never install a broker order executor.
set -euo pipefail
umask 077
root="$(cd -- "$(dirname -- "$0")/../.." && pwd -P)"
cd "$root"
if [[ "$(uname -s)" != "Linux" ]]; then
  echo "ERROR: This bootstrap is for AWS/Linux only." >&2
  exit 2
fi
python_cmd=""
for candidate in python3.12 python3.11 python3.10 python3; do
  if command -v "$candidate" >/dev/null 2>&1 &&
     "$candidate" -c 'import sys; sys.exit(sys.version_info < (3, 10))' >/dev/null 2>&1; then
    python_cmd="$candidate"
    break
  fi
done
if [[ -z "$python_cmd" ]]; then
  echo "ERROR: Python 3.10+ required. Install a supported Python version first." >&2
  exit 2
fi
"$python_cmd" scripts/aws/fxpro_preflight.py
venv="$HOME/.local/share/atlas-fxpro/venv"
mkdir -p "$HOME/.local/share/atlas-fxpro"
if [[ ! -x "$venv/bin/python" ]]; then
  "$python_cmd" -m venv "$venv"
fi
"$venv/bin/python" -m pip install --disable-pip-version-check "fastapi>=0.110,<1" "uvicorn>=0.30,<1" "websockets>=12,<18"
"$venv/bin/python" -c 'from scripts.atlas_provider_status import app; assert app is not None'
echo "FxPro AWS status-reader runtime installed."
echo "Run: bash scripts/aws/start_fxpro_readonly.sh"
