# ATLAS on AWS/Linux — FxPro cTrader read-only status

This setup is for AWS CloudShell testing or a private, persistent AWS Linux host.
It does **not** connect a brokerage account automatically, place PAPER or LIVE
orders, turn on execution, or change the ATLAS Council training journal.

## Quick start: AWS CloudShell (Android-compatible)

From the existing clone:

~~~bash
cd ~/atlas-tiger-shield
git pull --ff-only
bash scripts/aws/setup_fxpro_readonly.sh
python3 scripts/aws/fxpro_preflight.py
~~~

If setup reports that Python 3.10+ is missing, install a supported Python
version first. The bootstrap uses a separate isolated virtual environment
in the signed-in Linux user's home directory:
~/.local/share/atlas-fxpro/venv. It installs only FastAPI, Uvicorn and
websockets for the status reader. It does not edit the main ATLAS runtime.

In the same CloudShell tab, start the status reader in the foreground:

~~~bash
bash scripts/aws/start_fxpro_readonly.sh
~~~

It listens **only on 127.0.0.1:8766** and has no unauthenticated public access.
Stop it with Ctrl+C. Use another CloudShell tab to check configuration:

~~~bash
cd ~/atlas-tiger-shield
python3 scripts/aws/fxpro_preflight.py
~~~

Without credentials the status endpoints correctly refuse access; this
is a smoke-test of the code, not proof an FxPro account is connected.

## Private view-only authorization

In the official cTrader Open API developer portal, register/authorize an
application for **scope=accounts (SCOPE_VIEW)**, NOT trading scope.
Use FxPro cTrader accounts, not MT5 credentials. An account login number
or Gmail address by itself does not grant authorization. Each profile requires
an account login, cTrader OAuth access token, application client ID and secret.

Never paste account passwords, client secrets, OAuth tokens or bearer tokens
into chat, GitHub, screenshots or client-side Site configuration.

For DEMO set private environment variables:

- ATLAS_CTRADER_DEMO_LOGIN
- ATLAS_CTRADER_CLIENT_ID
- ATLAS_CTRADER_CLIENT_SECRET
- ATLAS_CTRADER_ACCESS_TOKEN
- ATLAS_PROVIDER_STATUS_TOKEN (random, >=24 characters)

For LIVE **read-only**, use separate values:

- ATLAS_CTRADER_LIVE_LOGIN
- ATLAS_CTRADER_LIVE_CLIENT_ID
- ATLAS_CTRADER_LIVE_CLIENT_SECRET
- ATLAS_CTRADER_LIVE_ACCESS_TOKEN
- ATLAS_PROVIDER_LIVE_STATUS_TOKEN (random, >=24 characters, distinct from DEMO)

Use AWS Secrets Manager with an instance IAM role for a persistent host;
inject secrets only into the server process at runtime. Do not commit an
environment file. All status checks intentionally print only CONNECTED,
NOT CONFIGURED or UNAVAILABLE; they never print account balances or credentials.

With credentials safely injected, check the profile and start locally:

~~~bash
cd ~/atlas-tiger-shield
python3 scripts/aws/fxpro_preflight.py --require both
bash scripts/aws/start_fxpro_readonly.sh
~~~

In a second CloudShell tab with the same secrets available securely:

~~~bash
cd ~/atlas-tiger-shield
python3 scripts/aws/check_fxpro_readonly.py --mode both
~~~

The expected success message is CONNECTED / READ_ONLY / NO BROKER ORDERS
for each authorized account. Authentication, provider access and live account
status are not verified just because the service started.

## Safety, network and hosting boundaries

The launcher forces paper/no-order flags and rejects any conflicting inherited
execution settings, including ATLAS_LIVE_TRADING=true. The LIVE account status
is informational only; it cannot place orders or finance PAPER simulations.

AWS CloudShell is not a 24/7 hosting environment and does not expose inbound
ports. For durable deployment, use a private EC2/Lightsail Linux instance
with a dedicated least-privilege service user and a systemd service.
Keep the listener bound to localhost and restrict all inbound traffic.
If Tiger Shield needs access, add a separately authenticated HTTPS reverse
proxy/bridge with strict authorization and private server-side tokens.
**Do not expose TCP/8766 publicly or place API tokens in browser code.**

The existing ChatGPT Site is not redeployed by these scripts. Council training
still requires genuine settled PAPER observations, not fabricated history.

## Verification

~~~bash
python3 -m pytest tests/test_aws_fxpro_readonly.py \
  tests/test_provider_status.py tests/test_ctrader_demo.py \
  tests/test_ctrader_live_status.py -q
~~~

Reference: README_MT5.md describes the FxPro cTrader status routes.
