from __future__ import annotations

import asyncio
import json
import os
import sys
from collections.abc import Awaitable, Callable
from typing import Any

from openai import AsyncOpenAI, APIConnectionError, APIStatusError, OpenAIError


PROJECT_ID = os.getenv("OPENAI_PROJECT_ID", "proj_V3bmvxhDANZ7tenDvgJSLxV6")
DEFAULT_MESSAGE = os.getenv(
    "OPENAI_AGENT_MESSAGE",
    "Introduce yourself as the configured data analyst, confirm the session is working, "
    "and briefly explain what information you would request before analyzing a business metric.",
)

AGENT_CONFIG: dict[str, Any] = {
    "name": "New agent",
    "model": "gpt-6-astra",
    "instructions": (
        "You are a data analyst who turns business questions into reproducible, evidence-based answers.\n\n"
        "1. Clarify the metric, population, date range, and comparison the user needs. Check available business definitions and note any ambiguity before choosing an interpretation.\n"
        "2. Discover the datasets and schemas available through supplied files or configured read-only database scripts or command-line tools. Do not assume a warehouse connection, table names, or column meanings. If the required data is unavailable, explain what is needed.\n"
        "3. Inspect data types, grain, join keys, time zones, missing values, and duplicates. Write read-only queries or analysis code, using bounded exploration before larger queries. Never modify database records, schemas, or permissions.\n"
        "4. Validate totals and joins, account for incomplete time periods, and investigate surprising results. Distinguish correlation from causation and identify limitations that could change the conclusion.\n"
        "5. Present the answer with supporting figures, a useful table or chart when appropriate, and the queries or calculations needed to reproduce it. Cite the data source and time range.\n\n"
        "Use existing metric definitions and analysis notes when supplied. Only claim to have saved reusable context when you have actually written it to an available, user-authorized location."
    ),
    "reasoning": {
        "effort": "medium",
        "summary": "auto",
    },
    "text": {
        "format": {"type": "text"},
        "verbosity": "medium",
    },
}


ToolHandler = Callable[[dict[str, Any]], Awaitable[Any] | Any]
TOOL_HANDLERS: dict[str, ToolHandler] = {}


def to_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if hasattr(value, "to_dict"):
        return value.to_dict()
    raise TypeError(f"Cannot convert {type(value)!r} to dict")


async def run_tool_handler(name: str, arguments: dict[str, Any]) -> tuple[bool, str]:
    handler = TOOL_HANDLERS.get(name)
    if handler is None:
        return False, f"No local handler is registered for tool '{name}'."

    try:
        result = handler(arguments)
        if asyncio.iscoroutine(result):
            result = await result
        if isinstance(result, str):
            return True, result
        return True, json.dumps(result, ensure_ascii=False)
    except Exception as exc:  # Tool failures should be returned to the agent, not crash the app.
        return False, f"{type(exc).__name__}: {exc}"


async def handle_required_actions(client: AsyncOpenAI, session_id: str) -> None:
    session = await client.beta.agents.sessions.retrieve(session_id)
    actions = getattr(session, "required_actions", None) or []

    for raw_action in actions:
        action = to_dict(raw_action)
        action_type = action.get("type")

        if action_type == "function_call":
            name = str(action.get("name", ""))
            arguments = action.get("arguments") or {}
            if not isinstance(arguments, dict):
                arguments = {"value": arguments}

            success, payload = await run_tool_handler(name, arguments)
            event: dict[str, Any] = {
                "type": "agent.session.input.tool_result",
                "turn_id": action["turn_id"],
                "call_id": action["call_id"],
                "success": success,
            }
            if success:
                event["output"] = payload
            else:
                event["error"] = payload

            await client.beta.agents.sessions.events.create(
                session_id,
                events=[event],
            )
            print(f"\n[tool] {name}: {'ok' if success else 'error'}", flush=True)
            continue

        if action_type == "environment_connection":
            raise RuntimeError(
                "The session requested an environment connection, but this app uses "
                "an OpenAI-hosted sandbox and has no external environment connector configured."
            )

        raise RuntimeError(f"Unsupported required action: {action}")


async def print_event(client: AsyncOpenAI, session_id: str, event: Any) -> bool:
    data = to_dict(event)
    event_type = data.get("type", "unknown")

    if event_type == "agent.session.turn.output_text.delta":
        delta = data.get("delta", "")
        if delta:
            print(delta, end="", flush=True)
        return False

    if event_type == "agent.session.turn.output_text.done":
        return False

    if event_type == "agent.session.requires_action":
        await handle_required_actions(client, session_id)
        return False

    if event_type == "error":
        error = data.get("error") or {}
        message = error.get("message") if isinstance(error, dict) else str(error)
        raise RuntimeError(message or "Agents API stream error")

    if event_type in {"agent.session.failed", "agent.session.environment.failed"}:
        raise RuntimeError(f"Agent lifecycle failure: {event_type}")

    if event_type == "agent.session.turn.failed":
        turn = data.get("turn") or {}
        if turn.get("subagent_id") is None:
            error = turn.get("error") or {}
            detail = error.get("message", "") if isinstance(error, dict) else str(error)
            raise RuntimeError(f"{event_type}: {detail}")
        return False

    if event_type == "agent.session.turn.cancelled":
        turn = data.get("turn") or {}
        if turn.get("subagent_id") is None:
            raise RuntimeError("The root agent turn was cancelled.")
        return False

    if event_type == "agent.session.turn.completed":
        turn = data.get("turn") or {}
        if turn.get("subagent_id") is None:
            print("\n\n[event] root turn completed", flush=True)
            return True
        return False

    # Keep lifecycle/tool visibility without dumping large payloads.
    if event_type not in {"agent.session.idle"}:
        print(f"\n[event] {event_type}", flush=True)

    return False


async def run(initial_message: str) -> int:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print(
            "OPENAI_API_KEY is not set. Export/set it in your shell before running.",
            file=sys.stderr,
        )
        return 2

    client = AsyncOpenAI(
        api_key=api_key,
        project=PROJECT_ID,
        timeout=360.0,
    )

    try:
        agent = await client.beta.agents.create(**AGENT_CONFIG)
        print(f"[agent] created: {agent.id}", flush=True)

        # Create the reusable-agent session first so we have a stable session ID,
        # then subscribe before sending input. This avoids missing early events.
        session = await client.beta.agents.sessions.create(
            agent_id=agent.id,
            environment={
                "type": "openai_hosted",
                "network": {"access": "disabled"},
            },
        )
        print(f"[session] created: {session.id}", flush=True)
        print(f"[project] {PROJECT_ID}", flush=True)
        print(f"[user] {initial_message}\n", flush=True)

        stream = await client.beta.agents.sessions.events.stream(session.id)
        try:
            await client.beta.agents.sessions.events.create(
                session.id,
                events=[
                    {
                        "type": "agent.session.input.message",
                        "input": [
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "input_text",
                                        "text": initial_message,
                                    }
                                ],
                            }
                        ],
                    }
                ],
            )

            async for event in stream:
                if await print_event(client, session.id, event):
                    break
            else:
                raise RuntimeError(
                    "The event stream closed before the root turn completed. "
                    "Retrieve the saved session/items to recover state."
                )
        finally:
            close = getattr(stream, "close", None)
            aclose = getattr(stream, "aclose", None)
            if callable(aclose):
                await aclose()
            elif callable(close):
                close()

        print(f"\n[done] agent_id={agent.id} session_id={session.id}", flush=True)
        return 0

    except APIStatusError as exc:
        print(
            f"OpenAI API error {exc.status_code}: {exc.message}",
            file=sys.stderr,
        )
        if getattr(exc, "request_id", None):
            print(f"request_id={exc.request_id}", file=sys.stderr)
        return 1
    except APIConnectionError as exc:
        print(f"OpenAI connection error: {exc}", file=sys.stderr)
        return 1
    except OpenAIError as exc:
        print(f"OpenAI SDK error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Application error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    finally:
        await client.close()


def main() -> int:
    message = " ".join(sys.argv[1:]).strip() or DEFAULT_MESSAGE
    return asyncio.run(run(message))


if __name__ == "__main__":
    raise SystemExit(main())
