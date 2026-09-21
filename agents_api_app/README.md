# OpenAI Agents API runner

This app creates the reusable **New agent** definition, then starts an Agents API session using the returned agent ID. It uses the official Python SDK, `AsyncOpenAI`, an OpenAI-hosted sandbox, event streaming, lifecycle/error handling, and required-action handling for function tools.

Default OpenAI project:

`proj_V3bmvxhDANZ7tenDvgJSLxV6`

## Requirements

- Python 3.10+
- An OpenAI API key that can access the project above
- `openai>=3.16.2,<4`
- `socksio>=1.0.0` for environments that use a SOCKS proxy through `HTTP_PROXY`, `HTTPS_PROXY`, or `ALL_PROXY`

The API key is read only from `OPENAI_API_KEY`. Do not commit it.

## Windows PowerShell

From the repository root:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r .\agents_api_app\requirements.txt

$env:OPENAI_API_KEY="YOUR_KEY_HERE"
$env:OPENAI_PROJECT_ID="proj_V3bmvxhDANZ7tenDvgJSLxV6"

python .\agents_api_app\main.py
```

Send a custom first user message:

```powershell
python .\agents_api_app\main.py "Summarize what you need before analyzing monthly revenue."
```

## Bash / macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r agents_api_app/requirements.txt

export OPENAI_API_KEY="YOUR_KEY_HERE"
export OPENAI_PROJECT_ID="proj_V3bmvxhDANZ7tenDvgJSLxV6"

python agents_api_app/main.py
```

## Runtime choice

The session uses:

```json
{
  "type": "openai_hosted",
  "network": { "access": "disabled" }
}
```

This avoids requiring a local/self-hosted executor for the initial runnable app. If you later need the agent to work directly against files or command-line tools on the ATLAS machine, switch deliberately to a self-hosted environment and add the appropriate environment connection/executor.

## Tool calls

The supplied agent definition contains no function tools, so the normal first run should not request any. The runner still handles `agent.session.requires_action`.

Add local handlers to `TOOL_HANDLERS` in `main.py` when you add function definitions to the saved agent. Unknown function calls are returned to the agent as failed tool results instead of crashing the process.

## What the program prints

- saved/reusable agent ID
- session ID
- project ID
- streamed output text
- lifecycle/tool events
- API/connection/application errors

Keep the printed agent ID if you want to reuse that same saved agent in a later version instead of creating a new one on each launch.
