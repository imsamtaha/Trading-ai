from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SECRET_MARKERS = ("KEY", "TOKEN", "SECRET", "PASSWORD", "CREDENTIAL")


def _is_secret_key(key: object) -> bool:
    text = str(key).upper()
    return any(marker in text for marker in SECRET_MARKERS)


def redact(value: object) -> object:
    if isinstance(value, dict):
        redacted: dict[str, object] = {}
        for key, item in value.items():
            key_text = str(key)
            redacted[key_text] = "***REDACTED***" if _is_secret_key(key_text) else redact(item)
        return redacted
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact(item) for item in value)
    return value


def _overall(groups: list[dict[str, Any]]) -> str:
    if any(group.get("status") == "FAIL" for group in groups):
        return "FAIL"
    if any(group.get("status") in {"NOT_RUN", "PARTIAL"} for group in groups):
        return "PARTIAL"
    return "PASS"


def build_report(commit_sha: str, groups: list[dict]) -> dict:
    sanitized_groups = redact(groups)
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "commit_sha": commit_sha,
        "overall": _overall(groups),
        "groups": sanitized_groups,
    }


def _markdown(report: dict) -> str:
    lines = [
        "# ATLAS Full Test Report",
        "",
        f"- Overall: **{report['overall']}**",
        f"- Commit: `{report['commit_sha']}`",
        f"- Generated: `{report['generated_at']}`",
        "",
        "| Group | Status | Required | Duration (s) | Reason |",
        "| --- | --- | --- | ---: | --- |",
    ]
    for group in report.get("groups", []):
        reason = str(group.get("reason", "")).replace("|", "\\|")
        duration = group.get("duration_seconds", "")
        lines.append(
            f"| {group.get('name', '')} | {group.get('status', '')} | "
            f"{group.get('required', False)} | {duration} | {reason} |"
        )
    lines.append("")
    return "\n".join(lines)


def write_report(report: dict, output_dir: str) -> tuple[str, str]:
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    safe_report = redact(report)
    json_path = target / "ATLAS_TEST_REPORT.json"
    md_path = target / "ATLAS_TEST_REPORT.md"
    json_path.write_text(json.dumps(safe_report, indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text(_markdown(safe_report), encoding="utf-8")
    return str(json_path), str(md_path)
