# OpenAI Agents API runner

This app creates the reusable **New agent** definition, then starts an Agents API session using the returned agent ID. It uses the official Python SDK, `AsyncOpenAI`, event streaming, lifecycle/error handling, and required-action handling for function tools.

Default OpenAI project:

`proj_V3bmvxhDANZ7tenDvgJSLxV6`

## Requirements

- Python 3.10+
- An OpenAI API key that can access the project above
- `openai>=3.16.2,<4`
- `python-dotenv>=1.0.1`
- `socksio>=1.0.0` only for environments that use a SOCKS proxy

The API key is read from `OPENAI_API_KEY`. The runner loads `agents_api_app/.env` automatically. Do not commit real secrets.

## Windows PowerShell

From the repository root:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r .\agents_api_app\requirements.txt

Copy-Item .\agents_api_app\.env.example .\agents_api_app\.env
notepad .\agents_api_app\.env

python .\agents_api_app\main.py
```

Or set variables directly in the shell:

```powershell
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

cp agents_api_app/.env.example agents_api_app/.env
nano agents_api_app/.env

python agents_api_app/main.py
```

Or export the variables directly:

```bash
export OPENAI_API_KEY="YOUR_KEY_HERE"
export OPENAI_PROJECT_ID="proj_V3bmvxhDANZ7tenDvgJSLxV6"
python agents_api_app/main.py
```

## Runtime choice

The session uses:

```json
{
  "type": "none"
}
```

That is intentional. The supplied agent definition does not include shell, filesystem, computer-use, or sandbox tools, so no runtime executor is needed. This keeps the first version runnable on Windows, Termux, Linux, and cloud hosts without a separate executor key or sandbox process.

If the agent is later given tools that require command execution or file access, switch deliberately to `openai_hosted` or `self_hosted`. A self-hosted environment requires a connected executor.

## Tool calls

The supplied agent definition contains no function tools, so a normal first run should not request one. The runner still handles `agent.session.requires_action` and returns `agent.session.input.tool_result` for function calls.

Add local handlers to `TOOL_HANDLERS` in `main.py` when function tools are added to the saved agent. Unknown function calls are returned to the agent as failed tool results instead of crashing the process.

## What the program prints

- saved/reusable agent ID
- session ID
- project ID
- streamed output text
- lifecycle/tool events
- API/connection/application errors

The app creates a new saved agent on each launch and prints its ID. Persist that ID if you want later launches to reuse the exact same saved agent instead of creating another one.
