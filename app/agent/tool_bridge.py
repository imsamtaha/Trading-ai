from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    access: str  # read | write
    provider: str


TOOL_SPECS: dict[str, ToolSpec] = {
    "github.read": ToolSpec("github.read", "Read repository, issue, PR, or code context.", "read", "github"),
    "github.write": ToolSpec("github.write", "Create or update GitHub content after approval.", "write", "github"),
    "gmail.read": ToolSpec("gmail.read", "Search and read mailbox context.", "read", "gmail"),
    "gmail.write": ToolSpec("gmail.write", "Draft, send, label, archive, or otherwise mutate mail after approval.", "write", "gmail"),
    "calendar.read": ToolSpec("calendar.read", "Read events and availability.", "read", "calendar"),
    "calendar.write": ToolSpec("calendar.write", "Create, update, delete, or respond to events after approval.", "write", "calendar"),
    "web.read": ToolSpec("web.read", "Perform external web research.", "read", "web"),
    "files.read": ToolSpec("files.read", "Search and read supported files.", "read", "files"),
    "files.write": ToolSpec("files.write", "Create or modify supported files after approval.", "write", "files"),
}


class ConnectorBridgeError(RuntimeError):
    pass


def bridge_status() -> dict[str, Any]:
    url = os.getenv("ATLAS_TOOL_BRIDGE_URL", "").strip()
    return {
        "configured": bool(url),
        "url_configured": bool(url),
        "tools": [asdict(spec) for spec in TOOL_SPECS.values()],
        "write_policy": "explicit_approval_required",
    }


def execute_tool(
    tool: str,
    arguments: dict[str, Any],
    *,
    approved: bool = False,
    timeout_seconds: float = 20.0,
) -> dict[str, Any]:
    spec = TOOL_SPECS.get(tool)
    if spec is None:
        raise ValueError(f"Unsupported right-hand tool: {tool}")
    if spec.access == "write" and not approved:
        return {
            "status": "APPROVAL_REQUIRED",
            "tool": tool,
            "provider": spec.provider,
            "message": "Explicit approval is required before this external mutation can run.",
        }

    bridge_url = os.getenv("ATLAS_TOOL_BRIDGE_URL", "").strip()
    if not bridge_url:
        return {
            "status": "NOT_CONFIGURED",
            "tool": tool,
            "provider": spec.provider,
            "message": "ATLAS_TOOL_BRIDGE_URL is not configured; no external action was executed.",
        }

    token = os.getenv("ATLAS_TOOL_BRIDGE_TOKEN", "").strip()
    payload = json.dumps({
        "tool": tool,
        "arguments": arguments,
        "approved": approved,
        "caller": "atlas-right-hand",
    }).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = Request(bridge_url.rstrip("/") + "/execute", data=payload, headers=headers, method="POST")
    try:
        with urlopen(req, timeout=timeout_seconds) as response:
            raw = response.read().decode("utf-8")
            data = json.loads(raw) if raw else {}
    except HTTPError as exc:
        raise ConnectorBridgeError(f"Tool bridge HTTP {exc.code}") from exc
    except URLError as exc:
        raise ConnectorBridgeError("Tool bridge is unreachable") from exc
    except json.JSONDecodeError as exc:
        raise ConnectorBridgeError("Tool bridge returned invalid JSON") from exc

    return {
        "status": "COMPLETED",
        "tool": tool,
        "provider": spec.provider,
        "result": data,
    }
